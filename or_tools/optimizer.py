from ortools.sat.python import cp_model
from datetime import datetime, timedelta

# Shared time slots generator
def generate_time_slots(start: datetime, hours: int = 24*14):
    return [start + timedelta(hours=i) for i in range(hours)]

# Main optimization function
def optimize_schedule(tasks: dict) -> list:
    model = cp_model.CpModel()
    solver = cp_model.CpSolver()
    variables = {}
    week_start = tasks['week_start']
    slots = generate_time_slots(week_start)

    blocked_slots = set()
    for fixed in tasks['fixed_tasks']:
        start = fixed['start']
        end = fixed['end']
        for i, slot in enumerate(slots):
            if start <= slot < end:
                blocked_slots.add(i)

    soft_blocked_slots = set()
    for i, slot in enumerate(slots):
        if 0 <= slot.hour < 7:
            soft_blocked_slots.add(i)

    academic_variables = {}
    for task in tasks.get('academic_tasks', []):
        sessions = []
        for i in range(task['total_hours'] // task['session_hours']):
            var = model.NewIntVar(0, len(slots)-1, f"{task['id']}_session_{i}")
            model.AddForbiddenAssignments([var], [[b] for b in blocked_slots])
            sessions.append(var)
        academic_variables[task['id']] = sessions

    for task in tasks['flexible_tasks']:
        sessions = []
        session_vars = []
        for i in range(task['total_hours'] // task['session_hours']):
            var = model.NewIntVar(0, len(slots)-1, f"{task['id']}_session_{i}")
            model.AddForbiddenAssignments([var], [[b] for b in blocked_slots])
            session_vars.append(var)
        for i in range(1, len(session_vars)):
            model.Add(session_vars[i] >= session_vars[i - 1] + 24)
        variables[task['id']] = session_vars

    for task in tasks['flexible_tasks']:
        for dep in task.get('dependencies', []):
            dep_vars = variables.get(dep) or academic_variables.get(dep)
            if dep_vars:
                for t_var in variables[task['id']]:
                    for d_var in dep_vars:
                        model.Add(t_var > d_var)

    penalty_vars = []
    for task_id, session_vars in variables.items():
        for var in session_vars:
            penalty = model.NewBoolVar(f"penalty_{task_id}_{var}")
            for s in soft_blocked_slots:
                model.Add(var == s).OnlyEnforceIf(penalty)
            penalty_vars.append(penalty)

    model.Minimize(sum(penalty_vars))

    solver.Solve(model)

    events = []
    for task_id, vars in variables.items():
        for i, var in enumerate(vars):
            start_index = solver.Value(var)
            start_time = slots[start_index]
            end_time = start_time + timedelta(hours=tasks['flexible_tasks'][0]['session_hours'])
            events.append({
                'id': f"{task_id}_{i}",
                'start_time': start_time,
                'end_time': end_time,
                'type': 'flexible_task'
            })

    for task_id, vars in academic_variables.items():
        for i, var in enumerate(vars):
            start_index = solver.Value(var)
            start_time = slots[start_index]
            end_time = start_time + timedelta(hours=tasks['academic_tasks'][0]['session_hours'])
            events.append({
                'id': f"{task_id}_{i}",
                'start_time': start_time,
                'end_time': end_time,
                'type': 'academic_task'
            })

    return events

# Update function
def update_schedule_with_new_tasks(old_events: list, new_tasks: dict) -> list:
    merged_fixed = [
        {
            'id': event['id'],
            'start': event['start_time'],
            'end': event['end_time'],
            'priority': event.get('priority', 1),
            'dependencies': []
        }
        for event in old_events
    ]
    new_tasks['fixed_tasks'].extend(merged_fixed)
    return optimize_schedule(new_tasks)
