from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


Department = Literal["Engineering", "S&T", "Traction"]
Priority = Literal["Critical", "High", "Medium", "Low"]


class TaskCreate(BaseModel):
    asset: str = Field(min_length=3, max_length=120)
    location: str = Field(min_length=3, max_length=120)
    department: Department
    corridor: str = Field(min_length=3, max_length=32)
    duration: int = Field(ge=1, le=12)
    priority: Priority = "Medium"


class PlanRequest(BaseModel):
    horizon: Literal["This week", "This month"] = "This week"


class DemoControl(BaseModel):
    action: Literal["pause", "resume", "reset", "set_speed"]
    speed: Literal[1, 2, 4] | None = None


class BlockWhatIf(BaseModel):
    start_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    date_iso: date


class BlockResources(BaseModel):
    manpower: Literal["Confirmed", "Pending", "Unavailable"]
    machines: Literal["Confirmed", "Pending", "Unavailable"]
    materials: Literal["Confirmed", "Pending", "Unavailable"]


class BlockUpdate(BaseModel):
    corridor: str = Field(min_length=3, max_length=32)
    section: str = Field(min_length=3, max_length=120)
    date_iso: date
    start_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    duration: int = Field(ge=1, le=24)
    departments: list[Department] = Field(min_length=1, max_length=3)
    tasks: int = Field(ge=0, le=100)
    status: Literal["Proposed", "Confirmed", "Under review", "Cancelled", "Emergency proposal"]
    trains: int = Field(ge=0, le=100)
    availability: float = Field(ge=0, le=100)
    resources: BlockResources
    confidence: int = Field(ge=1, le=100)
    reasoning: str = Field(min_length=3, max_length=500)


class TaskUpdate(BaseModel):
    asset: str = Field(min_length=3, max_length=120)
    location: str = Field(min_length=3, max_length=120)
    department: Department
    source: str = Field(min_length=2, max_length=32)
    priority: Priority
    due: str = Field(min_length=2, max_length=60)
    duration: int = Field(ge=1, le=12)
    corridor: str = Field(min_length=3, max_length=32)
    status: Literal["Unscheduled", "Scheduled", "In progress", "Completed", "Deferred", "Cancelled"]
    criticality: int = Field(ge=1, le=100)


class JointBlockRequest(BaseModel):
    departments: list[Department] = Field(min_length=1, max_length=3)
    task_ids: list[str] = Field(min_length=1, max_length=20)
    resources_confirmed: bool = False
