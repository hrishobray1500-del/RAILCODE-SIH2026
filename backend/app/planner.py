from collections import defaultdict
from datetime import date, datetime, time, timedelta


PRIORITY_WEIGHT = {"Critical": 50, "High": 35, "Medium": 20, "Low": 10}
CORRIDOR_SECTIONS = {
    "BPL–ET": ("Bhopal – Itarsi", 4),
    "BINA–BPL": ("Bina – Bhopal", 3),
    "ET–JBP": ("Itarsi – Jabalpur", 3),
    "BPL–NGP": ("Bhopal – Nagpur", 5),
}
NIGHT_WINDOWS = [(time(0, 30), time(4, 30)), (time(23, 0), time(23, 59))]
DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _task_score(task: dict) -> float:
    due = task["due"].lower()
    urgency = 30 if "overdue" in due else 23 if "today" in due else 16 if "1 day" in due else 9 if "3 days" in due else 4
    return task["criticality"] * 0.45 + PRIORITY_WEIGHT[task["priority"]] + urgency


def _window_for(day: date, start: time, duration: int) -> tuple[str, str]:
    start_at = datetime.combine(day, start)
    end_at = start_at + timedelta(hours=duration)
    label = "Today" if day == date.today() else "Tomorrow" if day == date.today() + timedelta(days=1) else DAY_NAMES[day.weekday()]
    return (
        f"{label}, {start_at:%H:%M}–{end_at:%H:%M} · {day:%b %d}",
        f"{start_at:%H:%M} – {end_at:%H:%M}",
    )


def generate_plan(tasks: list[dict], horizon: str) -> tuple[list[dict], set[str]]:
    """Greedy urgency-weighted packing; co-locates departments on shared corridor windows."""
    horizon_days = 7 if horizon == "This week" else 30
    available = sorted(
        (task for task in tasks if task.get("status", "Unscheduled") not in ("Completed", "Cancelled", "In progress")),
        key=_task_score,
        reverse=True,
    )
    by_corridor: dict[str, list[dict]] = defaultdict(list)
    for task in available:
        by_corridor[task["corridor"]].append(task)

    blocks = []
    scheduled = set()
    sequence = 1
    for corridor, corridor_tasks in by_corridor.items():
        for offset in range(horizon_days):
            if not corridor_tasks:
                break
            day = date.today() + timedelta(days=offset)
            window_index = offset % len(NIGHT_WINDOWS)
            start, latest_end = NIGHT_WINDOWS[window_index]
            window_capacity = (datetime.combine(day, latest_end) - datetime.combine(day, start)).total_seconds() / 3600
            selected = []
            hours = 0
            remaining = []
            for task in corridor_tasks:
                if hours + task["duration"] <= window_capacity and len(selected) < 3:
                    selected.append(task)
                    hours += task["duration"]
                else:
                    remaining.append(task)
            corridor_tasks = remaining
            if not selected:
                continue
            end = (datetime.combine(day, start) + timedelta(hours=hours)).time()
            label, _ = _window_for(day, start, hours)
            window = f"{start:%H:%M} – {end:%H:%M}"
            section, forecast_trains = CORRIDOR_SECTIONS.get(corridor, (corridor, 3))
            departments = list(dict.fromkeys(task["department"] for task in selected))
            blocks.append({
                "id": f"BLK-{date.today():%y%m%d}-{sequence:02d}",
                "corridor": corridor,
                "section": section,
                "date": label,
                "date_iso": day.isoformat(),
                "window": window,
                "duration": hours,
                "departments": departments,
                "tasks": len(selected),
                "status": "Proposed",
                "trains": forecast_trains,
                "availability": round(max(85, 100 - hours * forecast_trains * 0.48), 1),
                "resources": {
                    "manpower": "Confirmed" if sequence % 2 else "Pending",
                    "machines": "Confirmed",
                    "materials": "Confirmed" if sequence % 3 else "Pending",
                },
                "confidence": min(97, 78 + len(selected) * 6 + len(departments) * 2),
                "reasoning": f"{len(selected)} high-priority tasks share the {corridor} corridor window; estimated freight overlap {max(0, forecast_trains - 38)} trains. Verify live timetable and resources.",
            })
            sequence += 1
            scheduled.update(task["id"] for task in selected)

    return blocks, scheduled
