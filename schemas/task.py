from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Task(BaseModel):
    title: str
    description: str
    status: str
    priority: str
    deadline: datetime

class TaskCreate(Task):
    pass

class TaskUpdate(Task):
    title : Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    deadline: Optional[datetime] = None

class TaskInDB(Task):
    id: str
    created_at: datetime