import random
from datetime import datetime, timedelta


CORRIDOR_SCENARIOS = [
    {"name": "Bhopal – Itarsi", "code": "BPL – ET", "availability": 97.8, "target": 97.8, "minimum": 95.2, "maximum": 99.5, "trains": 42, "minimum_trains": 35, "maximum_trains": 48},
    {"name": "Bina – Bhopal", "code": "BINA – BPL", "availability": 94.2, "target": 94.2, "minimum": 90.8, "maximum": 97.5, "trains": 36, "minimum_trains": 29, "maximum_trains": 43},
    {"name": "Itarsi – Jabalpur", "code": "ET – JBP", "availability": 98.6, "target": 98.6, "minimum": 96.0, "maximum": 99.7, "trains": 28, "minimum_trains": 21, "maximum_trains": 34},
    {"name": "Bhopal – Nagpur", "code": "BPL – NGP", "availability": 91.5, "target": 91.5, "minimum": 88.0, "maximum": 95.0, "trains": 31, "minimum_trains": 24, "maximum_trains": 38},
]


def _status(availability: float) -> tuple[str, str]:
    if availability >= 95.5:
        return "On track", "green"
    if availability >= 92:
        return "Watch", "amber"
    return "At risk", "red"


class DemoSimulator:
    """Bounded, in-memory simulated railway telemetry. It never touches task records."""

    def __init__(self, seed: int | None = None):
        self._random = random.Random(seed)
        self.running = True
        self.speed = 1
        self._network = 96.4
        self._critical_assets = 98.2
        self._blocks_scheduled = 11
        self._block_utilization = 78.0
        self._tasks_coordinated = 24
        self._department_workload = {
            "Engineering": {"tasks": 7, "overdue": 2},
            "S&T": {"tasks": 5, "overdue": 1},
            "Traction": {"tasks": 4, "overdue": 1},
        }
        self._corridors = [dict(scenario) for scenario in CORRIDOR_SCENARIOS]
        self._integrations = [
            {"system": system, "external_status": "Not connected", "simulated_status": "Running", "latency_ms": self._random.randint(35, 180)}
            for system in ("TMS", "SMMS", "TDMS", "COA", "BDMS")
        ]
        self._changes = {
            "network_availability": 0,
            "critical_asset_availability": 0,
            "blocks_scheduled": 0,
            "tasks_coordinated": 0,
        }
        self._alert_states = [
            {"id": "ALT-001", "task_id": "TMS-2841", "asset": "Rail fracture inspection", "location": "KM 142/6 · BPL–ET", "department": "Engineering", "priority": "Critical", "age_minutes": 18, "open": True},
            {"id": "ALT-002", "task_id": "SMMS-1092", "asset": "Signal relay failure", "location": "Itarsi Jn · Panel B", "department": "S&T", "priority": "Critical", "age_minutes": 7, "open": True},
            {"id": "ALT-003", "task_id": "TDMS-0638", "asset": "OHE insulator degradation", "location": "KM 88/3 · BINA–BPL", "department": "Traction", "priority": "High", "age_minutes": 42, "open": True},
        ]
        self._ingestion_log = []
        self._record_ingestion_events()
        now = datetime.now()
        self._history = []
        for index in range(7):
            sample = self._random.gauss(self._network, 0.22)
            self._history.append({
                "day": (now - timedelta(seconds=2 * (6 - index))).strftime("%H:%M:%S"),
                "availability": round(max(94, min(99, sample)), 1),
                "blocks": max(1, min(5, self._blocks_scheduled + self._random.choice((-2, -1, 0, 1, 2)))),
            })

    def snapshot(self) -> dict:
        sampled_at = datetime.now().astimezone().isoformat(timespec="seconds")
        corridors = []
        for corridor in self._corridors:
            status, color = _status(corridor["availability"])
            corridors.append({
                "name": corridor["name"],
                "code": corridor["code"],
                "availability": round(corridor["availability"], 1),
                "trains": corridor["trains"],
                "status": status,
                "color": color,
            })
        return {
            "running": self.running,
            "speed": self.speed,
            "sampled_at": sampled_at,
            "network_availability": round(self._network, 1),
            "critical_asset_availability": round(self._critical_assets, 1),
            "blocks_scheduled": self._blocks_scheduled,
            "block_utilization": self._block_utilization,
            "tasks_coordinated": self._tasks_coordinated,
            "workload": {department: dict(metrics) for department, metrics in self._department_workload.items()},
            "changes": dict(self._changes),
            "corridors": corridors,
            "history": [dict(sample) for sample in self._history],
            "alerts": [dict(alert) for alert in self._alert_states if alert["open"]],
            "integrations": [dict(integration) for integration in self._integrations],
            "ingestion_log": [dict(item) for item in self._ingestion_log],
        }

    def _record_ingestion_events(self) -> None:
        now = datetime.now().astimezone()
        self._ingestion_log = [
            {"system": system, "event": event, "sampled_at": (now - timedelta(seconds=offset)).isoformat(timespec="seconds"), "status": "Simulated"}
            for system, event, offset in (
                ("COA", "Corridor window forecast refreshed", 1),
                ("TDMS", "OHE asset condition snapshot generated", 2),
                ("SMMS", "Signal defect feed generated", 3),
                ("TMS", "Track maintenance backlog refreshed", 5),
                ("BDMS", "Sample block utilization recalculated", 7),
            )
        ]

    def set_running(self, running: bool) -> None:
        self.running = running

    def set_speed(self, speed: int) -> None:
        if speed not in (1, 2, 4):
            raise ValueError("Simulation speed must be 1, 2, or 4.")
        self.speed = speed

    def reset(self) -> dict:
        self.__init__()
        return self.snapshot()

    def tick(self) -> dict:
        if self.running:
            return self.advance()
        return self.snapshot()

    def advance(self) -> dict:
        previous = {
            "network_availability": self._network,
            "critical_asset_availability": self._critical_assets,
            "blocks_scheduled": self._blocks_scheduled,
            "tasks_coordinated": self._tasks_coordinated,
        }
        for _ in range(self.speed):
            self._network = self._wander(self._network, 96.4, 94, 98.3, 0.17)
            self._critical_assets = self._wander(self._critical_assets, 98.2, 96.5, 99.4, 0.12)
            for corridor in self._corridors:
                corridor["availability"] = self._wander(
                    corridor["availability"], corridor["target"],
                    corridor["minimum"], corridor["maximum"], 0.2,
                )
                if self._random.random() < 0.32:
                    step = self._random.choice((-1, 1))
                    corridor["trains"] = max(
                        corridor["minimum_trains"],
                        min(corridor["maximum_trains"], corridor["trains"] + step),
                    )
            if self._random.random() < 0.3:
                self._blocks_scheduled = max(8, min(15, self._blocks_scheduled + self._random.choice((-1, 1))))
            if self._random.random() < 0.4:
                self._tasks_coordinated = max(18, min(30, self._tasks_coordinated + self._random.choice((-1, 1))))
            if self._random.random() < 0.35:
                self._block_utilization = round(max(62, min(94, self._block_utilization + self._random.choice((-2, -1, 1, 2)))), 1)
            for department, metrics in self._department_workload.items():
                if self._random.random() < 0.18:
                    metrics["tasks"] = max(2, min(14, metrics["tasks"] + self._random.choice((-1, 1))))
                if self._random.random() < 0.12:
                    metrics["overdue"] = max(0, min(metrics["tasks"], metrics["overdue"] + self._random.choice((-1, 1))))

        self._changes = {
            "network_availability": round(self._network - previous["network_availability"], 1),
            "critical_asset_availability": round(self._critical_assets - previous["critical_asset_availability"], 1),
            "blocks_scheduled": self._blocks_scheduled - previous["blocks_scheduled"],
            "tasks_coordinated": self._tasks_coordinated - previous["tasks_coordinated"],
        }
        self._history.append({
            "day": datetime.now().strftime("%H:%M:%S"),
            "availability": round(self._network, 1),
            "blocks": self._blocks_scheduled % 5 + 1,
        })
        self._history = self._history[-12:]
        for alert in self._alert_states:
            if alert["open"]:
                alert["age_minutes"] += 2 * self.speed
        if self._random.random() < 0.08:
            for alert in self._alert_states:
                if not alert["open"]:
                    alert["open"] = True
                    alert["age_minutes"] = 1
                    break
        elif self._random.random() < 0.035:
            open_alerts = [alert for alert in self._alert_states if alert["open"] and alert["priority"] != "Critical"]
            if open_alerts:
                self._random.choice(open_alerts)["open"] = False
        self._record_ingestion_events()
        return self.snapshot()

    def _wander(self, current: float, target: float, minimum: float, maximum: float, volatility: float) -> float:
        drift = (target - current) * 0.08
        movement = self._random.gauss(drift, volatility)
        return round(max(minimum, min(maximum, current + movement)), 2)
