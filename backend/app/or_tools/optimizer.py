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
    
    # Print detailed input information
    print(f"optimize_schedule called with week_start={week_start}")
    print(f"fixed_tasks count: {len(fixed_tasks)}")
    print(f"flexible_tasks count: {len(flexible_tasks)}")
    print(f"academic_tasks count: {len(academic_tasks)}")

    # 0 ── Basic validation --------------------------------------------------
    if not (fixed_tasks or flexible_tasks or academic_tasks):
        print("No tasks supplied → nothing to schedule")
        return []

    # Validate inputs more carefully to avoid cryptic errors
    for i, t in enumerate(flexible_tasks):
        print(f"Checking flexible task {i}: {t.get('id', 'unknown')}")
        if 'session_hours' not in t or 'total_hours' not in t:
            print(f"Warning: Task {t.get('id', 'unknown')} missing hours fields")
            # Assign default values rather than failing
            t['session_hours'] = t.get('session_hours', 1)
            t['total_hours'] = t.get('total_hours', 1)
            
        if not isinstance(t.get('session_hours', 0), (int, float)) or not isinstance(t.get('total_hours', 0), (int, float)):
            print(f"Warning: Task {t.get('id', 'unknown')} has non-numeric hours")
            # Convert to numeric
            try:
                t['session_hours'] = float(t.get('session_hours', 1))
                t['total_hours'] = float(t.get('total_hours', 1))
            except (ValueError, TypeError):
                t['session_hours'] = 1
                t['total_hours'] = 1
                
        # Ensure positive values
        if t.get('session_hours', 0) <= 0:
            print(f"Warning: Task {t.get('id', 'unknown')} has invalid session_hours, setting to 1")
            t['session_hours'] = 1
        if t.get('total_hours', 0) <= 0:
            print(f"Warning: Task {t.get('id', 'unknown')} has invalid total_hours, setting to 1")
            t['total_hours'] = 1
    
    # Do similar validation for academic tasks
    for i, t in enumerate(academic_tasks):
        print(f"Checking academic task {i}: {t.get('id', 'unknown')}")
        if 'session_hours' not in t or 'total_hours' not in t:
            print(f"Warning: Academic task {t.get('id', 'unknown')} missing hours fields")
            t['session_hours'] = t.get('session_hours', 1)
            t['total_hours'] = t.get('total_hours', 1)
            
        if not isinstance(t.get('session_hours', 0), (int, float)) or not isinstance(t.get('total_hours', 0), (int, float)):
            print(f"Warning: Academic task {t.get('id', 'unknown')} has non-numeric hours")
            try:
                t['session_hours'] = float(t.get('session_hours', 1))
                t['total_hours'] = float(t.get('total_hours', 1))
            except (ValueError, TypeError):
                t['session_hours'] = 1
                t['total_hours'] = 1
                
        # Ensure positive values
        if t.get('session_hours', 0) <= 0:
            print(f"Warning: Academic task {t.get('id', 'unknown')} has invalid session_hours, setting to 1")
            t['session_hours'] = 1
        if t.get('total_hours', 0) <= 0:
            print(f"Warning: Academic task {t.get('id', 'unknown')} has invalid total_hours, setting to 1")
            t['total_hours'] = 1

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
    
    # Filter flexible tasks based on their start_date
    # If a task has a start_date in the future, respect it
    filtered_flex_tasks = []
    for task in flexible_tasks:
        # If task has a deadline (end_date), ensure it's after week_start
        # But don't skip tasks that haven't ended yet
        if task.get("deadline"):
            # Convert deadline to datetime if it's a string
            deadline = task["deadline"]
            if isinstance(deadline, str):
                try:
                    # Don't import datetime here, it's already imported at the top
                    deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                    task["deadline"] = deadline  # Update with converted value
                except Exception as e:
                    print(f"Error converting deadline string to datetime: {e}")
                    deadline = None  # Don't use invalid deadline for comparison
            
            # Now compare with week_start only if it's a valid datetime
            if isinstance(deadline, datetime) and deadline < week_start:
                print(f"Skipping expired task {task['id']} with deadline {deadline}")
                continue
        
        # Always include tasks for scheduling
        filtered_flex_tasks.append(task)
        print(f"Including task {task['id']} for scheduling")
    
    # Don't proceed if no flexible tasks were found
    if not filtered_flex_tasks and flexible_tasks:
        print("WARNING: All flexible tasks were filtered out! Check filtering logic.")
    
    flex_pool = filtered_flex_tasks + study_sessions

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
