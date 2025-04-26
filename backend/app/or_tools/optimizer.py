# optimizer.py – Unified rescheduling & OR‑Tools solver
"""Planner.AI scheduler – overlap‑safe & window‑aware (28 Apr 2025)

Fixes
-----
1. **Respect original `start_date`/`end_date` for previously‑scheduled tasks**
   We re‑query their `FlexibleObligation` rows so reclaimed tasks keep their
   original time window.
2. **No overlap between any sessions (flex‑vs‑flex)**
   Replaced pairwise hack with proper **`AddNoOverlap`** using interval vars and
   fixed intervals for the already‑blocked fixed events.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from ortools.sat.python import cp_model

from app.models.schedule import CalendarEvent, FlexibleObligation

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════════════════

def update_schedule(db: Session, *, student_id: int) -> None:
    """Re‑optimise a student’s calendar after any change."""
    logger.info("Re‑scheduling calendar for student %s", student_id)

    events = db.scalars(select(CalendarEvent).where(CalendarEvent.student_id == student_id)).all()
    fixed_events, old_flex_events = _partition_events(events)

    # ── Unscheduled obligations (new)
    scheduled_ids = {e.flexible_obligation_id for e in old_flex_events if e.flexible_obligation_id}
    unscheduled = db.scalars(
        select(FlexibleObligation)
        .where(
            FlexibleObligation.student_id == student_id,
            FlexibleObligation.obligation_id.not_in(scheduled_ids),
        )
    ).all()

    # ── Map of all flex obligation rows we’ll need (for windows/session hrs)
    needed_ids = scheduled_ids.union(o.obligation_id for o in unscheduled)
    flex_rows_map = {row.obligation_id: row for row in db.scalars(
        select(FlexibleObligation).where(FlexibleObligation.obligation_id.in_(needed_ids))
    ).all()}

    fixed_payload = [_ce_to_dict(e) for e in fixed_events]
    prev_tasks   = _regroup_old_flex(old_flex_events, flex_rows_map)
    new_tasks    = [_flex_to_task(o) for o in unscheduled]
    flex_payload = prev_tasks + new_tasks

    if not flex_payload:
        return

    sessions = _solve_with_or_tools(fixed_payload, flex_payload)
    _replace_flexible_events(db, student_id, old_flex_events, sessions)
    logger.info("Inserted %d sessions", len(sessions))

# ════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════

def _ce_to_dict(ev: CalendarEvent) -> Dict[str, Any]:
    return {"date": ev.date, "start": ev.start_time, "end": ev.end_time}


def _flex_to_task(ob: FlexibleObligation) -> Dict[str, Any]:
    c = ob.constraints or {}
    return {
        "id": ob.obligation_id,
        "total_hours": float(ob.weekly_target_hours),
        "session_hours": c.get("session_hours", 1),
        "start_date": ob.start_date,
        "end_date": ob.end_date,
        "priority": ob.priority or 3,
    }


def _partition_events(evts: List[CalendarEvent]) -> Tuple[List[CalendarEvent], List[CalendarEvent]]:
    fixed, flex = [], []
    for e in evts:
        if e.event_type == "fixed_obligation":
            fixed.append(e)
        elif e.event_type in {"flexible_obligation", "study_session"}:
            flex.append(e)
    return fixed, flex


def _regroup_old_flex(events: List[CalendarEvent], flex_map: Dict[int, FlexibleObligation]) -> List[Dict[str, Any]]:
    grouped: Dict[int, Dict[str, Any]] = {}
    for ev in events:
        fid = ev.flexible_obligation_id
        if not fid:
            continue
        base = flex_map.get(fid)
        session_hours = (base.constraints or {}).get("session_hours", 1) if base else 1
        t = grouped.setdefault(fid, {
            "id": fid,
            "total_hours": 0.0,
            "session_hours": session_hours,
            "start_date": base.start_date if base else None,
            "end_date": base.end_date if base else None,
            "priority": base.priority if base else 3,
        })
        t["total_hours"] += (ev.end_time - ev.start_time).seconds / 3600
    return list(grouped.values())


def _replace_flexible_events(db: Session, student_id: int, old_flex: List[CalendarEvent], new: List[Dict[str, Any]]):
    if old_flex:
        db.execute(delete(CalendarEvent).where(CalendarEvent.event_id.in_([e.event_id for e in old_flex])))

    db.add_all([
        CalendarEvent(
            student_id=student_id,
            event_type="flexible_obligation",
            flexible_obligation_id=s["flexible_obligation_id"],
            date=s["date"],
            start_time=s["start"],
            end_time=s["end"],
            priority=s.get("priority", 3),
            status="scheduled",
        )
        for s in new
    ])
    db.commit()

# ════════════════════════════════════════════════════════════════════════════
# OR‑Tools solver (global NoOverlap)
# ════════════════════════════════════════════════════════════════════════════

def _solve_with_or_tools(fixed_events: List[Dict[str, Any]], flex_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Schedule with a *night‑time preference*:

    * 23:00‑08:00 slots are **disfavoured**. We try a first pass where they are
      completely forbidden. If the model is infeasible we relax the constraint
      and allow night placement.
    """
    import math

    model = cp_model.CpModel()

    now = datetime.utcnow()
    earliest_start_raw = min([now] + [t["start_date"] for t in flex_tasks if t["start_date"]] + [f["start"] for f in fixed_events])
    earliest_start = earliest_start_raw.replace(hour=0, minute=0, second=0, microsecond=0)
    latest_end  = max([now] + [t["end_date"] for t in flex_tasks if t["end_date"]] + [f["end"] for f in fixed_events])
    horizon_end = latest_end.replace(hour=23, minute=59)

    slot_min = 30
    n_slots = int((horizon_end - earliest_start).total_seconds() / 60 / slot_min)
    if n_slots <= 0:
        raise ValueError("Empty horizon")

    def idx(dt: datetime) -> int:
        return int((dt - earliest_start).total_seconds() / 60 / slot_min)

    # Helper to compute slot -> datetime
    def slot_time(i: int) -> datetime:
        return earliest_start + timedelta(minutes=i * slot_min)

    # ------------------------------------------------------------------
    # Build intervals (fixed + flex) and a list of candidate models
    # ------------------------------------------------------------------
    def build_model(block_night: bool):
        m = cp_model.CpModel()
        intervals = []
        session_records = []

        # Fixed intervals ------------------------------------------------
        for f in fixed_events:
            s = idx(f["start"])
            dur = math.ceil((f["end"] - f["start"]).total_seconds() / 60 / slot_min)
            intervals.append(m.NewFixedSizeIntervalVar(s, dur, f"fixed_{s}"))

        # Night slots ----------------------------------------------------
        night_block = set()
        if block_night:
            for s in range(n_slots):
                t = slot_time(s)
                if t.hour >= 23 or t.hour < 8:
                    night_block.add(s)

        # Flexible sessions ---------------------------------------------
        for task in flex_tasks:
            dur_slots = math.ceil(task["session_hours"] * 60 / slot_min)
            n_sess = max(1, int(math.ceil(task["total_hours"] / task["session_hours"])))

            window_start = task["start_date"] or earliest_start
            window_end   = (task["end_date"] or horizon_end) - timedelta(minutes=dur_slots * slot_min)
            low, high = max(0, idx(window_start)), min(n_slots - dur_slots, idx(window_end))
            if high < low:
                raise RuntimeError(f"No window for task {task['id']}")

            for i in range(n_sess):
                start = m.NewIntVar(low, high, f"s_{task['id']}_{i}")
                if block_night and night_block:
                    m.AddForbiddenAssignments([start], [[b] for b in night_block])
                ivar  = m.NewIntervalVar(start, dur_slots, start + dur_slots, f"iv_{task['id']}_{i}")
                intervals.append(ivar)
                session_records.append((start, dur_slots, task))

        m.AddNoOverlap(intervals)

        makespan = m.NewIntVar(0, n_slots, "makespan")
        for s, d, _ in session_records:
            m.Add(makespan >= s + d)
        m.Minimize(makespan)

        return m, session_records

    # First attempt: night blocked --------------------------------------
    for attempt, allow_night in enumerate([False, True], start=1):
        mdl, rec = build_model(block_night=not allow_night)
        solver = cp_model.CpSolver(); solver.parameters.max_time_in_seconds = 10
        result = solver.Solve(mdl)
        if result in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            session_records = rec
            break
        if allow_night:
            raise RuntimeError("No feasible schedule, even with night hours allowed")

    # Build output ------------------------------------------------------
    outs = []
    for s, d, t in session_records:
        start_idx = solver.Value(s)
        start_dt  = earliest_start + timedelta(minutes=start_idx * slot_min)
        end_dt    = start_dt + timedelta(minutes=d * slot_min)
        outs.append({
            "flexible_obligation_id": t["id"],
            "priority": t.get("priority", 3),
            "date": start_dt.replace(hour=0, minute=0, second=0, microsecond=0),
            "start": start_dt,
            "end": end_dt,
        })
    return outs
