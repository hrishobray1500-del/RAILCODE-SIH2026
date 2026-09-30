import os
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator


DATABASE_PATH = os.environ.get("DATABASE_PATH", str(Path(__file__).resolve().parents[2] / "data" / "railplan.db"))

SEED_TASKS = [
    ("TMS-2841", "Rail fracture inspection", "KM 142/6 · BPL–ET", "Engineering", "TMS", "Critical", "Overdue 2 days", 3, "BPL–ET", "Unscheduled", 96),
    ("SMMS-1092", "Signal relay replacement", "Itarsi Jn · Panel B", "S&T", "SMMS", "High", "Due today", 2, "BPL–ET", "Unscheduled", 84),
    ("TDMS-0638", "OHE insulator renewal", "KM 88/3 · BINA–BPL", "Traction", "TDMS", "High", "Due in 1 day", 3, "BINA–BPL", "Unscheduled", 79),
    ("TMS-2790", "Points & crossing lubrication", "Bhopal Jn · Line 4", "Engineering", "TMS", "Medium", "Due in 3 days", 2, "BPL–ET", "Unscheduled", 62),
    ("SMMS-1065", "Track circuit calibration", "KM 56/2 · BINA–BPL", "S&T", "SMMS", "Medium", "Due in 5 days", 2, "BINA–BPL", "Unscheduled", 54),
    ("TDMS-0612", "Cantilever assembly inspection", "KM 176/1 · BPL–ET", "Traction", "TDMS", "Low", "Due in 8 days", 2, "BPL–ET", "Unscheduled", 38),
]

TASK_COLUMNS = "id, asset, location, department, source, priority, due, duration, corridor, status, criticality"


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def task_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def block_dict(row: sqlite3.Row) -> dict:
    from json import loads

    block = dict(row)
    block["departments"] = loads(block.pop("departments_json"))
    block["resources"] = loads(block.pop("resources_json"))
    return block


def initialize() -> None:
    with connect() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, asset TEXT NOT NULL, location TEXT NOT NULL,
                department TEXT NOT NULL, source TEXT NOT NULL, priority TEXT NOT NULL,
                due TEXT NOT NULL, duration INTEGER NOT NULL, corridor TEXT NOT NULL,
                status TEXT NOT NULL, criticality INTEGER NOT NULL
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS blocks (
                id TEXT PRIMARY KEY, corridor TEXT NOT NULL, section TEXT NOT NULL,
                date TEXT NOT NULL, window TEXT NOT NULL, duration INTEGER NOT NULL,
                departments_json TEXT NOT NULL, tasks INTEGER NOT NULL, status TEXT NOT NULL,
                trains INTEGER NOT NULL, availability REAL NOT NULL,
                date_iso TEXT NOT NULL DEFAULT '', resources_json TEXT NOT NULL DEFAULT '{}',
                confidence INTEGER NOT NULL DEFAULT 75, reasoning TEXT NOT NULL DEFAULT ''
            )"""
        )
        block_columns = {row["name"] for row in connection.execute("PRAGMA table_info(blocks)")}
        for name, definition in (
            ("date_iso", "TEXT NOT NULL DEFAULT ''"),
            ("resources_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("confidence", "INTEGER NOT NULL DEFAULT 75"),
            ("reasoning", "TEXT NOT NULL DEFAULT ''"),
        ):
            if name not in block_columns:
                connection.execute(f"ALTER TABLE blocks ADD COLUMN {name} {definition}")
        connection.execute(
            "UPDATE blocks SET date_iso = ? WHERE date_iso = ''",
            (date.today().isoformat(),),
        )
        connection.execute(
            """UPDATE blocks
               SET resources_json = '{"manpower":"Confirmed","machines":"Confirmed","materials":"Pending"}'
               WHERE resources_json = '{}'"""
        )
        connection.execute(
            """UPDATE blocks
               SET reasoning = 'Illustrative sample block; verify live timetable, resource readiness, worksite protection and required approval.'
               WHERE reasoning = ''"""
        )
        if connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
            connection.executemany(
                f"INSERT INTO tasks ({TASK_COLUMNS}) VALUES ({','.join('?' for _ in range(11))})",
                SEED_TASKS,
            )
        if connection.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 0:
            today = date.today()
            seed_blocks = [
                ("BLK-2401", "BPL–ET", "Bhopal – Itarsi", f"Today, 01:15–04:15 · {today:%b %d}", "01:15 – 04:15", 3, '["Engineering", "S&T"]', 2, "Confirmed", 4, 92.0, today.isoformat(), '{"manpower":"Confirmed","machines":"Confirmed","materials":"Confirmed"}', 91, "Rail inspection and signal relay works share a corridor window. Verify actual timetable, resources and worksite protection."),
                ("BLK-2402", "BINA–BPL", "Bina – Bhopal", f"Tomorrow, 00:30–03:30 · {today + timedelta(days=1):%b %d}", "00:30 – 03:30", 3, '["Traction"]', 1, "Proposed", 3, 95.0, (today + timedelta(days=1)).isoformat(), '{"manpower":"Pending","machines":"Confirmed","materials":"Confirmed"}', 83, "OHE maintenance is grouped into an overnight corridor window; verify live traffic and crew availability."),
                ("BLK-2403", "BPL–ET", "Bhopal – Itarsi", f"Wed, 02:00–04:00 · {today + timedelta(days=2):%b %d}", "02:00 – 04:00", 2, '["Engineering"]', 1, "Proposed", 5, 91.0, (today + timedelta(days=2)).isoformat(), '{"manpower":"Confirmed","machines":"Confirmed","materials":"Pending"}', 79, "Track inspection is tentatively placed in a low-traffic sample window; forecast is illustrative."),
            ]
            connection.executemany(
                """INSERT INTO blocks (id, corridor, section, date, window, duration,
                   departments_json, tasks, status, trains, availability, date_iso,
                   resources_json, confidence, reasoning)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                seed_blocks,
            )


def get_tasks() -> list[dict]:
    with connect() as connection:
        rows = connection.execute(f"SELECT {TASK_COLUMNS} FROM tasks ORDER BY criticality DESC").fetchall()
    return [task_dict(row) for row in rows]


def get_blocks() -> list[dict]:
    with connect() as connection:
        rows = connection.execute("SELECT * FROM blocks ORDER BY rowid").fetchall()
    return [block_dict(row) for row in rows]


def insert_task(task: dict) -> list[dict]:
    with connect() as connection:
        last_id = connection.execute("SELECT id FROM tasks WHERE source = 'Manual' ORDER BY id DESC LIMIT 1").fetchone()
        sequence = int(last_id["id"].split("-")[-1]) + 1 if last_id else 1
        task_id = f"MAN-{sequence:04d}"
        criticality = {"Critical": 96, "High": 82, "Medium": 60, "Low": 38}[task["priority"]]
        connection.execute(
            f"INSERT INTO tasks ({TASK_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (task_id, task["asset"], task["location"], task["department"], "Manual",
             task["priority"], "Just added", task["duration"], task["corridor"],
             "Unscheduled", criticality),
        )
    return get_tasks()


def update_task(task_id: str, values: dict) -> dict | None:
    with connect() as connection:
        if connection.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,)).fetchone() is None:
            return None
        assignments = ", ".join(f"{column} = ?" for column in values)
        connection.execute(
            f"UPDATE tasks SET {assignments} WHERE id = ?",
            (*values.values(), task_id),
        )
        row = connection.execute(f"SELECT {TASK_COLUMNS} FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return task_dict(row)


def move_block(block_id: str, start_time: str, date_iso: str) -> dict | None:
    start_hour, start_minute = (int(part) for part in start_time.split(":"))
    with connect() as connection:
        row = connection.execute("SELECT * FROM blocks WHERE id = ?", (block_id,)).fetchone()
        if row is None:
            return None
        end_minutes = start_hour * 60 + start_minute + row["duration"] * 60
        end_time = f"{(end_minutes // 60) % 24:02d}:{end_minutes % 60:02d}"
        window = f"{start_time} – {end_time}"
        block_date = date.fromisoformat(date_iso)
        date_label = f"{block_date:%a, %d %b} · {window}"
        connection.execute(
            "UPDATE blocks SET window = ?, date = ?, date_iso = ?, status = 'Proposed' WHERE id = ?",
            (window, date_label, date_iso, block_id),
        )
        updated = connection.execute("SELECT * FROM blocks WHERE id = ?", (block_id,)).fetchone()
    return block_dict(updated)


def update_block(block_id: str, values: dict) -> dict | None:
    from json import dumps
    from datetime import date as calendar_date

    start_time = values["start_time"]
    duration = values["duration"]
    start_hour, start_minute = (int(part) for part in start_time.split(":"))
    end_minutes = start_hour * 60 + start_minute + duration * 60
    end_time = f"{(end_minutes // 60) % 24:02d}:{end_minutes % 60:02d}"
    date_iso = values["date_iso"].isoformat()
    scheduled_date = calendar_date.fromisoformat(date_iso)
    date_label = f"{scheduled_date:%a, %d %b} · {start_time} – {end_time}"
    with connect() as connection:
        if connection.execute("SELECT 1 FROM blocks WHERE id = ?", (block_id,)).fetchone() is None:
            return None
        connection.execute(
            """UPDATE blocks
               SET corridor = ?, section = ?, date = ?, window = ?, duration = ?,
                   departments_json = ?, tasks = ?, status = ?, trains = ?,
                   availability = ?, date_iso = ?, resources_json = ?,
                   confidence = ?, reasoning = ?
               WHERE id = ?""",
            (values["corridor"], values["section"], date_label,
             f"{start_time} – {end_time}", duration, dumps(values["departments"]),
             values["tasks"], values["status"], values["trains"],
             values["availability"], date_iso, dumps(values["resources"]),
             values["confidence"], values["reasoning"], block_id),
        )
        updated = connection.execute("SELECT * FROM blocks WHERE id = ?", (block_id,)).fetchone()
    return block_dict(updated)


def insert_emergency_block(task: dict, date_iso: str, window: str) -> dict:
    from json import dumps
    from uuid import uuid4
    from datetime import date as calendar_date

    start_time = window.split(" – ")[0]
    with connect() as connection:
        block_id = f"EMG-{uuid4().hex[:8].upper()}"
        scheduled_date = calendar_date.fromisoformat(date_iso)
        duration = min(task["duration"], 4)
        end_minutes = int(start_time[:2]) * 60 + int(start_time[3:]) + duration * 60
        end_time = f"{(end_minutes // 60) % 24:02d}:{end_minutes % 60:02d}"
        actual_window = f"{start_time} – {end_time}"
        resources = {"manpower": "Pending", "machines": "Pending", "materials": "Pending"}
        reasoning = f"Emergency proposal for {task['asset']} ({task['id']}); prioritized as {task['priority']}. Validate emergency protection, timetable, resources and authorized approval."
        connection.execute(
            """INSERT INTO blocks (id, corridor, section, date, window, duration,
               departments_json, tasks, status, trains, availability, date_iso,
               resources_json, confidence, reasoning)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (block_id, task["corridor"], task["location"], f"{scheduled_date:%a, %d %b} · {actual_window}",
             actual_window, duration, dumps([task["department"]]), 1, "Emergency proposal", 3, 90.0,
             date_iso, dumps(resources), 96 if task["priority"] == "Critical" else 88, reasoning),
        )
        row = connection.execute("SELECT * FROM blocks WHERE id = ?", (block_id,)).fetchone()
    return block_dict(row)


def create_joint_request(block_id: str, request: dict) -> dict:
    from json import dumps
    from uuid import uuid4
    from datetime import datetime, timezone

    with connect() as connection:
        if connection.execute("SELECT 1 FROM blocks WHERE id = ?", (block_id,)).fetchone() is None:
            raise LookupError("The proposed block does not exist.")
        request_id = f"JNT-{uuid4().hex[:8].upper()}"
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS joint_requests (
                id TEXT PRIMARY KEY, block_id TEXT NOT NULL,
                departments_json TEXT NOT NULL, task_ids_json TEXT NOT NULL,
                resources_confirmed INTEGER NOT NULL, status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            """INSERT INTO joint_requests
               (id, block_id, departments_json, task_ids_json, resources_confirmed, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (request_id, block_id, dumps(request["departments"]), dumps(request["task_ids"]),
             int(request["resources_confirmed"]), "Ready for review" if request["resources_confirmed"] else "Resources pending",
             created_at),
        )
    return {
        "id": request_id,
        "block_id": block_id,
        "departments": request["departments"],
        "task_ids": request["task_ids"],
        "resources_confirmed": request["resources_confirmed"],
        "status": "Ready for review" if request["resources_confirmed"] else "Resources pending",
        "created_at": created_at,
    }


def get_joint_requests() -> list[dict]:
    from json import loads

    with connect() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS joint_requests (
                id TEXT PRIMARY KEY, block_id TEXT NOT NULL,
                departments_json TEXT NOT NULL, task_ids_json TEXT NOT NULL,
                resources_confirmed INTEGER NOT NULL, status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        rows = connection.execute("SELECT * FROM joint_requests ORDER BY created_at DESC").fetchall()
    return [
        {
            "id": row["id"],
            "block_id": row["block_id"],
            "departments": loads(row["departments_json"]),
            "task_ids": loads(row["task_ids_json"]),
            "resources_confirmed": bool(row["resources_confirmed"]),
            "status": row["status"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def save_plan(blocks: list[dict], scheduled_task_ids: set[str]) -> None:
    from json import dumps

    with connect() as connection:
        connection.execute("DELETE FROM blocks")
        connection.executemany(
            """INSERT INTO blocks (id, corridor, section, date, window, duration,
               departments_json, tasks, status, trains, availability, date_iso,
               resources_json, confidence, reasoning)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (block["id"], block["corridor"], block["section"], block["date"],
                 block["window"], block["duration"], dumps(block["departments"]),
                 block["tasks"], block["status"], block["trains"], block["availability"],
                 block.get("date_iso", ""), dumps(block.get("resources", {})),
                 block.get("confidence", 75), block.get("reasoning", ""))
                for block in blocks
            ],
        )
        if scheduled_task_ids:
            connection.execute("UPDATE tasks SET status = 'Unscheduled' WHERE status NOT IN ('Completed', 'Cancelled', 'In progress')")
            placeholders = ",".join("?" for _ in scheduled_task_ids)
            connection.execute(
                f"UPDATE tasks SET status = 'Scheduled' WHERE id IN ({placeholders}) AND status NOT IN ('Completed', 'Cancelled', 'In progress')",
                tuple(scheduled_task_ids),
            )
        else:
            connection.execute("UPDATE tasks SET status = 'Unscheduled' WHERE status NOT IN ('Completed', 'Cancelled', 'In progress')")
