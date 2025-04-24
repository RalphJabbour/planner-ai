"""Core scheduling engine powered by Google OR‑Tools (CP‑SAT).

This file purposely contains MANY inline comments so newcomers can follow the
constraint‑programming logic step‑by‑step.

Four event types supported:
1. FixedObligation      – hard‑blocked calendar slots (lectures, meetings …)
2. FlexibleObligation   – tasks without strict time but MUST happen (gym, chores)
3. AcademicTask         – a deliverable that only has a *deadline* (exam, project)
4. StudySession         – generated work chunks needed to finish an AcademicTask

StudySession behaves like FlexibleObligation but is **linked** back to its
origin AcademicTask via the `parent_task_id` field so we can trace completion.

NOTE: Any DB queries / ORM calls are *NOT* in this file. They belong to the
service layer so the solver stays pure‑python and testable.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from ortools.sat.python import cp_model

# ---------------------------------------------------------------------------
# Utility helpers (imported in service.py too) – feel free to move to utils.py
# ---------------------------------------------------------------------------

HOURS_IN_TWO_WEEKS = 24 * 14  # default schedule horizon
SLEEP_START = 0               # 00:00 → midnight
SLEEP_END   = 7               # 07:00 → 7 AM


def generate_time_slots(start: datetime, hours: int = HOURS_IN_TWO_WEEKS) -> List[datetime]:
    """Return a list of *hour‑granular* datetime objects from `start`."""
    return [start + timedelta(hours=i) for i in range(hours)]


# ---------------------------------------------------------------------------
# Core solver
# ---------------------------------------------------------------------------

def optimize_schedule(
    *,
    week_start: datetime,
    fixed_tasks: List[Dict],
    flexible_tasks: List[Dict],
    academic_tasks: List[Dict],
    preferences: Dict | None = None,
) -> List[Dict]:
    """Compute an optimized calendar as a list of event‑dicts.

    Parameters
    ----------
    week_start        : Start of the two‑week horizon (should be a Monday 00:00)
    fixed_tasks       : Hard‑blocked events. Keys: id,start,end,priority
    flexible_tasks    : Tasks with total_hours & session_hours and optional
                         dependencies / per‑day limits.
    academic_tasks    : Same keys as flexible_tasks BUT they represent goals
                         (assignment/exam) rather than sessions. They will be
                         EXPANDED into StudySession chunks internally.
    preferences       : Optional behaviour hints (peak_hours, max_hours_per_day…)
    """

    # ------------------------------------------------------------------
    # 0.  Pre‑processing / defaults
    # ------------------------------------------------------------------
    prefs = {
        "peak_hours":        preferences.get("peak_hours", [] if preferences else []),
        "max_hours_per_day": preferences.get("max_hours_per_day", 6 if preferences else 6),
        "min_gap_between":   preferences.get("min_gap_between_sessions", 1),
    } if preferences else {
        "peak_hours": [],
        "max_hours_per_day": 6,
        "min_gap_between": 1,
    }

    # Expand academic_tasks into study sessions » behaves like flexible
    study_sessions: List[Dict] = []
    for task in academic_tasks:
        chunks = task["total_hours"] // task["session_hours"]
        for idx in range(chunks):
            study_sessions.append(
                {
                    "id": f"{task['id']}_session{idx}",
                    "parent_task_id": task["id"],
                    "total_hours": task["session_hours"],
                    "session_hours": task["session_hours"],
                    "deadline": task["deadline"],
                    "priority": task.get("priority", 5),
                    "dependencies": task.get("dependencies", []),
                    "is_study": True,
                }
            )

    # Merge flexible tasks and study_sessions for uniform treatment
    flex_pool = flexible_tasks + study_sessions

    # ------------------------------------------------------------------
    # 1.  Build solver model
    # ------------------------------------------------------------------
    model = cp_model.CpModel()
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10  # <- safety limit

    slots = generate_time_slots(week_start)
    blocked_slots_hard = set()

    # 1a. Hard‑block fixed obligations + mandatory sleep hours
    for ev in fixed_tasks:
        for idx, slot in enumerate(slots):
            if ev["start"] <= slot < ev["end"]:
                blocked_slots_hard.add(idx)
    for idx, slot in enumerate(slots):
        if SLEEP_START <= slot.hour < SLEEP_END:
            blocked_slots_hard.add(idx)

    # 1b. Create decision variables for every *hour‑session* to schedule
    task_vars: Dict[str, List[cp_model.IntVar]] = {}
    daily_load: Dict[Tuple[int, int], List[cp_model.IntVar]] = {}
    # key (day_index, student)   – student=0 (single user)

    for task in flex_pool:
        sessions = []
        n_sessions = task["total_hours"] // task["session_hours"]
        for s in range(n_sessions):
            var = model.NewIntVar(0, len(slots)-1, f"{task['id']}_s{s}")
            # forbid hard blocked slots
            model.AddForbiddenAssignments([var], [[b] for b in blocked_slots_hard])
            sessions.append(var)
            # Collect per‑day load to limit daily hours later
            for d_idx in range(len(slots)//24):
                daily_load.setdefault((d_idx, 0), []).append(var)
        task_vars[task["id"]] = sessions

    # 1c.  Enforce *spacing* between sessions of SAME task
    for task in flex_pool:
        ses = task_vars[task["id"]]
        gap = prefs["min_gap_between"]
        for i in range(1, len(ses)):
            model.Add(ses[i] >= ses[i-1] + gap)

    # 1d.  Handle dependencies (task B > task A)
    for task in flex_pool:
        for dep in task.get("dependencies", []):
            if dep in task_vars:
                for t_var in task_vars[task["id"]]:
                    for d_var in task_vars[dep]:
                        model.Add(t_var >= d_var + 1)  # at least next hour

    # 1e.  Daily study‑hour cap (soft)
    daily_penalties: List[cp_model.IntVar] = []
    cap = prefs["max_hours_per_day"]
    for day in range(len(slots)//24):
        load_count = []
        for task in flex_pool:
            for var in task_vars[task["id"]]:
                # indicator if var falls on this day
                ind = model.NewBoolVar(f"day{day}_{var}")
                start_idx = day*24
                end_idx   = (day+1)*24 - 1
                model.Add(var >= start_idx).OnlyEnforceIf(ind)
                model.Add(var <= end_idx).OnlyEnforceIf(ind)
                load_count.append(ind)
        # sum > cap ⇒ penalty
        excess = model.NewIntVar(0, len(load_count), f"excess_day{day}")
        model.Add(excess == sum(load_count) - cap).OnlyEnforceIf(excess > 0)
        daily_penalties.append(excess)

    # 1f. Soft‑penalty for using sleep hours (already blocked hard, but if ever
    #      nothing fits we could allow by removing them from blocked_slots_hard
    #      and adding a very high penalty; omitted for brevity.)

    # ------------------------------------------------------------------
    # 2.  Objective – minimise total penalty & honour task priorities
    # ------------------------------------------------------------------
    penalty_weight = 100  # huge weight so solver avoids penalties first
    priority_weight = 1   # then tries to satisfy high priorities earlier

    objective_terms = [penalty_weight * p for p in daily_penalties]

    # Simple objective: earliest finishing time weighted by priority
    for task in flex_pool:
        for var in task_vars[task["id"]]:
            objective_terms.append(priority_weight * task.get("priority", 1) * var)

    model.Minimize(sum(objective_terms))

    # ------------------------------------------------------------------
    # 3.  Solve & build event list
    # ------------------------------------------------------------------
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Return empty list – caller should handle infeasible schedules
        return []

    events: List[Dict] = []
    # Append existing fixed tasks first (caller may decide to keep/remove)
    for ev in fixed_tasks:
        events.append(
            {
                "id": ev["id"],
                "start_time": ev["start"],
                "end_time":   ev["end"],
                "type": "fixed_obligation",
            }
        )

    # Add new flexible / study sessions from solver values
    for task in flex_pool:
        duration = timedelta(hours=task["session_hours"])
        for idx, var in enumerate(task_vars[task["id"]]):
            start = slots[solver.Value(var)]
            events.append(
                {
                    "id": f"{task['id']}_{idx}",
                    "start_time": start,
                    "end_time": start + duration,
                    "type": "study_session" if task.get("is_study") else "flexible_obligation",
                    "parent_task_id": task.get("parent_task_id"),
                }
            )

    return events


# update_schedule_with_new_tasks() remains unchanged – just calls optimize

def update_schedule_with_new_tasks(old_events: List[Dict], new_payload: Dict) -> List[Dict]:
    """Merge old events as fixed, then call optimize_schedule with new tasks."""
    fixed_from_old = [
        {
            "id": ev["id"],
            "start": ev["start_time"],
            "end":   ev["end_time"],
            "priority": ev.get("priority", 1),
        }
        for ev in old_events
    ]
    return optimize_schedule(
        week_start=new_payload["week_start"],
        fixed_tasks=fixed_from_old + new_payload.get("fixed_tasks", []),
        flexible_tasks=new_payload.get("flexible_tasks", []),
        academic_tasks=new_payload.get("academic_tasks", []),
        preferences=new_payload.get("preferences", {}),
    )

