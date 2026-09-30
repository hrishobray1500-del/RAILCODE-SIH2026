import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import database
from .planner import generate_plan
from .schemas import BlockUpdate, BlockWhatIf, DemoControl, JointBlockRequest, PlanRequest, TaskCreate, TaskUpdate
from .simulation import DemoSimulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("railplan")


class UpdateHub:
    def __init__(self):
        self.clients: set[WebSocket] = set()

    async def connect(self, socket: WebSocket) -> None:
        await socket.accept()
        self.clients.add(socket)

    def disconnect(self, socket: WebSocket) -> None:
        self.clients.discard(socket)

    async def publish(self, message: dict) -> None:
        stale = []
        for socket in self.clients:
            try:
                await socket.send_json(message)
            except (RuntimeError, WebSocketDisconnect):
                stale.append(socket)
        for socket in stale:
            self.disconnect(socket)


hub = UpdateHub()
simulator = DemoSimulator()


async def run_simulator() -> None:
    while True:
        await asyncio.sleep(2)
        if simulator.running:
            await hub.publish({"type": "simulation", "data": simulator.tick()})


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.initialize()
    simulation_task = asyncio.create_task(run_simulator())
    logger.info("RAILCODE demo API ready; simulated telemetry will refresh every 2 seconds.")
    try:
        yield
    finally:
        simulation_task.cancel()
        try:
            await simulation_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="RAILCODE Block Planning API",
    description="Demo API for coordinated railway maintenance block planning with simulated telemetry.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "railcode-api", "mode": "demo"}


@app.get("/api/demo/status")
def demo_status():
    return simulator.snapshot()


@app.post("/api/demo/control")
async def demo_control(control: DemoControl):
    if control.action == "pause":
        simulator.set_running(False)
    elif control.action == "resume":
        simulator.set_running(True)
    elif control.action == "reset":
        simulator.reset()
    elif control.action == "set_speed":
        if control.speed is None:
            raise HTTPException(status_code=422, detail="Select a supported simulation speed: 1x, 2x, or 4x.")
        simulator.set_speed(control.speed)
    snapshot = simulator.snapshot()
    await hub.publish({"type": "simulation", "data": snapshot})
    return snapshot


@app.post("/api/alerts/{alert_id}/emergency-block")
async def propose_emergency_block(alert_id: str):
    alert = next((item for item in simulator.snapshot()["alerts"] if item["id"] == alert_id), None)
    if alert is None:
        raise HTTPException(status_code=404, detail="This simulated alert is not active.")
    task = next((item for item in database.get_tasks() if item["id"] == alert["task_id"]), None)
    if task is None:
        raise HTTPException(status_code=404, detail="The sample maintenance task for this alert was not found.")
    emergency_date = datetime.now().date()
    if datetime.now().hour >= 4:
        emergency_date += timedelta(days=1)
    try:
        block = database.insert_emergency_block(task, emergency_date.isoformat(), "00:30 – 04:30")
    except Exception:
        logger.exception("Failed to create an emergency block proposal for simulated alert %s.", alert_id)
        raise HTTPException(status_code=500, detail="The emergency block proposal could not be saved.") from None
    await hub.publish({"type": "refresh", "resource": "emergency-block"})
    return {"block": block, "simulated": True, "approval_required": True}


@app.get("/api/tasks")
def list_tasks():
    return database.get_tasks()


@app.post("/api/tasks", status_code=201)
async def create_task(task: TaskCreate):
    try:
        tasks = database.insert_task(task.model_dump())
    except Exception:
        logger.exception("Failed to persist a maintenance task.")
        raise HTTPException(status_code=500, detail="The maintenance task could not be saved.") from None
    await hub.publish({"type": "refresh", "resource": "tasks"})
    return tasks


@app.patch("/api/tasks/{task_id}")
async def edit_task(task_id: str, update: TaskUpdate):
    try:
        task = database.update_task(task_id, update.model_dump())
    except Exception:
        logger.exception("Failed to update maintenance task %s.", task_id)
        raise HTTPException(status_code=500, detail="The maintenance task could not be updated.") from None
    if task is None:
        raise HTTPException(status_code=404, detail="The selected maintenance task was not found.")
    await hub.publish({"type": "refresh", "resource": "tasks", "id": task_id})
    return task


@app.get("/api/blocks")
def list_blocks():
    return database.get_blocks()


@app.patch("/api/blocks/{block_id}")
async def edit_block(block_id: str, update: BlockUpdate):
    try:
        block = database.update_block(block_id, update.model_dump())
    except Exception:
        logger.exception("Failed to update block proposal %s.", block_id)
        raise HTTPException(status_code=500, detail="The block proposal could not be updated.") from None
    if block is None:
        raise HTTPException(status_code=404, detail="The selected block was not found.")
    conflicts = [
        other["id"] for other in database.get_blocks()
        if other["id"] != block_id
        and other["corridor"] == block["corridor"]
        and other["date_iso"] == block["date_iso"]
        and int(other["window"][:2]) * 60 + int(other["window"][3:5])
        < int(block["window"][:2]) * 60 + int(block["window"][3:5]) + block["duration"] * 60
        and int(other["window"][8:10]) * 60 + int(other["window"][11:13])
        > int(block["window"][:2]) * 60 + int(block["window"][3:5])
    ]
    await hub.publish({"type": "refresh", "resource": "blocks", "id": block_id})
    return {"block": block, "conflicting_blocks": conflicts, "approval_required": True}


@app.post("/api/plan/generate")
async def create_plan(request: PlanRequest):
    try:
        tasks = database.get_tasks()
        blocks, scheduled = generate_plan(tasks, request.horizon)
        database.save_plan(blocks, scheduled)
        refreshed_tasks = database.get_tasks()
    except Exception:
        logger.exception("Failed to generate or persist a block schedule.")
        raise HTTPException(status_code=500, detail="The block schedule could not be generated.") from None
    await hub.publish({"type": "refresh", "resource": "plan"})
    return {
        "horizon": request.horizon,
        "blocks": database.get_blocks(),
        "tasks": refreshed_tasks,
        "tasks_scheduled": len(scheduled),
        "tasks_unscheduled": len(tasks) - len(scheduled),
        "method": "urgency-weighted corridor and department coordination",
        "approval_required": True,
    }


@app.get("/api/command")
def command_dashboard():
    task_data = database.get_tasks()
    block_data = database.get_blocks()
    simulated = simulator.snapshot()
    corridor_health = {
        corridor["code"].replace(" ", ""): corridor["availability"]
        for corridor in simulated["corridors"]
    }
    workload = {
        department: {
            "tasks": sum(
                task["department"] == department and task["status"] not in ("Completed", "Cancelled", "In progress")
                for task in task_data
            ),
            "overdue": sum(
                task["department"] == department
                and task["status"] not in ("Completed", "Cancelled", "In progress")
                and "Overdue" in task["due"]
                for task in task_data
            ),
        }
        for department in ("Engineering", "S&T", "Traction")
    }
    enriched_tasks = [
        {
            **task,
            "base_criticality": task["criticality"],
            "zone": "Bhopal Division",
            "asset_type": "Track" if task["department"] == "Engineering" else "Signal" if task["department"] == "S&T" else "OHE",
            "overdue": "Overdue" in task["due"],
            "criticality": max(1, min(100, round(
                task["criticality"] * 0.78
                + {"Critical": 19, "High": 13, "Medium": 7, "Low": 2}[task["priority"]]
                + (8 if "Overdue" in task["due"] else 0)
                + max(0, 96 - corridor_health.get(task["corridor"].replace(" ", ""), 96)) * 0.6
            ))),
        }
        for task in task_data
    ]
    cluster_members: dict[str, list[dict]] = {}
    for task in enriched_tasks:
        cluster_members.setdefault(task["corridor"], []).append(task)
    clusters = [
        {
            "corridor": corridor,
            "section": tasks[0]["location"],
            "task_ids": [task["id"] for task in tasks],
            "departments": list(dict.fromkeys(task["department"] for task in tasks)),
            "count": len(tasks),
            "critical": sum(task["priority"] in ("Critical", "High") for task in tasks),
            "saving_hours": max(1, len(tasks) - 1),
            "proximity_method": "Tasks share an illustrative corridor; precise geographic coordinates are not connected.",
        }
        for corridor, tasks in cluster_members.items() if len(tasks) > 1
    ]
    return {
        "mode": "demo",
        "simulated": True,
        "simulation": simulated,
        "tasks": enriched_tasks,
        "blocks": block_data,
        "workload": workload,
        "clusters": clusters,
        "block_utilization": simulator.snapshot()["block_utilization"],
        "projected_availability": round(min(99.5, simulated["network_availability"] + 1.6), 1),
        "joint_requests": database.get_joint_requests(),
    }


@app.post("/api/blocks/{block_id}/what-if")
async def block_what_if(block_id: str, request: BlockWhatIf):
    existing_blocks = database.get_blocks()
    block = database.move_block(block_id, request.start_time, request.date_iso.isoformat())
    if block is None:
        raise HTTPException(status_code=404, detail="The selected block was not found.")
    hour = int(request.start_time[:2])
    passenger_delays = max(0, (hour - 1) % 6 - 2)
    freight_delays = max(0, (hour + block["trains"]) % 5 - 2)
    impact = {
        "passenger_trains_delayed": passenger_delays,
        "freight_trains_delayed": freight_delays,
        "estimated_delay_minutes": passenger_delays * 12 + freight_delays * 20,
        "availability_change": round(-min(1.5, (passenger_delays + freight_delays) * 0.2), 1),
        "reason": "Illustrative timetable-overlap estimate; verify against the live control-office timetable before approval.",
    }
    start_minutes = hour * 60 + int(request.start_time[3:])
    end_minutes = start_minutes + block["duration"] * 60
    conflicting_blocks = [
        other["id"] for other in existing_blocks
        if other["id"] != block_id
        and other["corridor"] == block["corridor"]
        and other["date_iso"] == request.date_iso.isoformat()
        and int(other["window"][:2]) * 60 + int(other["window"][3:5]) < end_minutes
        and int(other["window"][8:10]) * 60 + int(other["window"][11:13]) > start_minutes
    ]
    impact["conflicting_blocks"] = conflicting_blocks
    if conflicting_blocks:
        impact["estimated_delay_minutes"] += 30 * len(conflicting_blocks)
        impact["reason"] += f" Potential overlap with {len(conflicting_blocks)} other same-corridor block(s)."
    await hub.publish({"type": "refresh", "resource": "plan"})
    return {"block": block, "impact": impact, "simulated": True, "approval_required": True}


@app.post("/api/blocks/{block_id}/joint-request")
async def joint_block_request(block_id: str, request: JointBlockRequest):
    task_ids = {task["id"] for task in database.get_tasks()}
    unknown = set(request.task_ids) - task_ids
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown maintenance task IDs: {', '.join(sorted(unknown))}")
    try:
        joint_request = database.create_joint_request(block_id, request.model_dump())
    except LookupError:
        raise HTTPException(status_code=404, detail="The selected block was not found.") from None
    await hub.publish({"type": "refresh", "resource": "coordination"})
    return joint_request


@app.websocket("/ws/updates")
async def updates(socket: WebSocket):
    await hub.connect(socket)
    try:
        while True:
            await socket.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(socket)
