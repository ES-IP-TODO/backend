import enum
import uuid
from typing import List, Optional

from sqlalchemy import (ARRAY, Boolean, Column, DateTime, Enum, Float,
                        ForeignKey, Integer, String, Text)

from db.database import Base


class TaskStatus(enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in-progress"
    DONE = "done"

class TaskPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    description = Column(String(2048), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO, nullable=False)
    created_at = Column(DateTime, nullable=False)
    priority = Column(Enum(TaskPriority), nullable=False)
    deadline = Column(DateTime, nullable=False)
    user_id = Column(String, ForeignKey("user.id"), nullable=False)