from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.database import get_db
from models.task import Task as TaskModel
from schemas.task import TaskCreate, TaskInDB, TaskUpdate


def create_task(task: TaskCreate, user_id: str, db: Session = Depends(get_db)):
    db_task = TaskModel(
        title=task.title,
        description=task.description,
        created_at=datetime.now(timezone.utc),
        priority=task.priority,
        deadline=task.deadline,
        user_id=user_id,
    )

    try:
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while creating the task.") from e

    return db_task

def get_task_by_user_id(user_id: str, db: Session = Depends(get_db)):
    tasks = db.query(TaskModel).filter(TaskModel.user_id == user_id).all()
    return tasks

def get_task_by_id(task_id: str, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

def get_task_by_status(status: str, db: Session = Depends(get_db)):
    tasks = db.query(TaskModel).filter(TaskModel.status == status).all()
    return tasks

def update_task(task_id: str, task: TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(TaskModel).filter(TaskModel.id == task_id).first()

    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    for attr, value in task.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(db_task, attr, value)

    try:
        db.commit()
        db.refresh(db_task)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while updating the task.") from e

    return db_task