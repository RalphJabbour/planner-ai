"""
Core scheduling engine ― Google OR-Tools CP-SAT
Supports:
  1. fixed_tasks      (hard-blocked events)
  2. flexible_tasks   (total_hours / session_hours / dependencies)
  3. academic_tasks   (expanded into study sessions)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from ortools.sat.python import cp_model

HOURS_IN_TWO_WEEKS = 24 * 14
SLEEP_START, SLEEP_END = 0, 7  # hard block 00:00-06:59


# ---------------------------------------------------------------------------

def _slots(start: datetime, hours: int = HOURS_IN_TWO_WEEKS) -> List[datetime]:
    return [start + timedelta(hours=i) for i in range(hours)]


# ---------------------------------------------------------------------------

def optimize_schedule(
    *,
    week_start: datetime,
    fixed_tasks: List[Dict],
    flexible_tasks: List[Dict],
    academic_tasks: List[Dict],
    preferences: Dict | None = None,
) -> List[Dict]:
    """
    Return list of calendar-event dicts (empty if infeasible).

    Raises ValueError on obviously bad input (≤0 hours, etc.).
    """

    # 0 ── Basic validation --------------------------------------------------
    if not (fixed_tasks or flexible_tasks or academic_tasks):
        print("No tasks supplied → nothing to schedule")
        return []

    for t in flexible_tasks + academic_tasks:
        if t["session_hours"] <= 0 or t["total_hours"] <= 0:
            raise ValueError(f"{t['id']}: hours must be positive")

    prefs = preferences or {}
    prefs.setdefault("max_hours_per_day", 6)
    prefs.setdefault("min_gap_between_sessions", 1)

    # -- expand academic_tasks → study sessions
    study_sessions: List[Dict] = []
    for task in academic_tasks:
        n = max(1, task["total_hours"] // task["session_hours"])
        for i in range(n):
            study_sessions.append(
                {
                    "id": f"{task['id']}_s{i}",
                    "parent_task_id": task["id"],
                    "total_hours": task["session_hours"],
                    "session_hours": task["session_hours"],
                    "deadline": task["deadline"],
                    "priority": task.get("priority", 8),
                    "dependencies": task.get("dependencies", []),
                    "is_study": True,
                }
            )

    flex_pool = flexible_tasks + study_sessions

    # 1 ── Build CP-SAT model ----------------------------------------------
    model = cp_model.CpModel()
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10

    slots = _slots(week_start)
    blocked_hard = set()

    for ev in fixed_tasks:
        for idx, slot in enumerate(slots):
            if ev["start"] <= slot < ev["end"]:
                blocked_hard.add(idx)
    for idx, slot in enumerate(slots):
        if SLEEP_START <= slot.hour < SLEEP_END:
            blocked_hard.add(idx)

    task_vars: Dict[str, List[cp_model.IntVar]] = {}

    # 1b ── decision vars
    for task in flex_pool:
        vars_: List[cp_model.IntVar] = []
        n_sessions = int(max(1, task["total_hours"] // task["session_hours"]))
        for s in range(n_sessions):
            v = model.NewIntVar(0, len(slots) - 1, f"{task['id']}_{s}")
            model.AddForbiddenAssignments([v], [[b] for b in blocked_hard])
            vars_.append(v)
        task_vars[task["id"]] = vars_

    # spacing between sessions of same task
    gap = prefs["min_gap_between_sessions"]
    for task in flex_pool:
        ses = task_vars[task["id"]]
        for i in range(1, len(ses)):
            model.Add(ses[i] >= ses[i - 1] + gap)

    # dependencies
    for task in flex_pool:
        for dep in task.get("dependencies", []):
            if dep in task_vars:
                for t_var in task_vars[task["id"]]:
                    for d_var in task_vars[dep]:
                        model.Add(t_var >= d_var + 1)

    # 1e ── soft daily cap
    daily_penalties = []
    cap = prefs["max_hours_per_day"]
    days = len(slots) // 24

    for d in range(days):
        ind_vars: List[cp_model.BoolVar] = []
        start_idx, end_idx = d * 24, (d + 1) * 24 - 1
        for task in flex_pool:
            for v in task_vars[task["id"]]:
                ind = model.NewBoolVar(f"d{d}_{v.Name()}")
                model.Add(v >= start_idx).OnlyEnforceIf(ind)
                model.Add(v <= end_idx).OnlyEnforceIf(ind)
                model.Add(v < start_idx).OnlyEnforceIf(ind.Not())
                ind_vars.append(ind)

        load = model.NewIntVar(0, len(ind_vars), f"load_d{d}")
        excess = model.NewIntVar(0, len(ind_vars), f"excess_d{d}")
        model.Add(load == sum(ind_vars))
        model.Add(excess >= load - cap)
        model.Add(excess >= 0)
        daily_penalties.append(excess)

    # 2 ── objective
    model.Minimize(
        100 * sum(daily_penalties)
        + sum(var for vars_ in task_vars.values() for var in vars_)
    )

    # 3 ── solve
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("Solver returned infeasible / unknown")
        return []

    # 4 ── build result list
    events: List[Dict] = [
        {
            "id": ev["id"],
            "start_time": ev["start"],
            "end_time": ev["end"],
            "type": "fixed_obligation",
        }
        for ev in fixed_tasks
    ]

    for task in flex_pool:
        dur = timedelta(hours=task["session_hours"])
        for idx, v in enumerate(task_vars[task["id"]]):
            st = slots[solver.Value(v)]
            events.append(
                {
                    "id": f"{task['id']}_{idx}",
                    "start_time": st,
                    "end_time": st + dur,
                    "type": "study_session" if task.get("is_study") else "flexible_obligation",
                    "parent_task_id": task.get("parent_task_id"),
                }
            )

    return events
