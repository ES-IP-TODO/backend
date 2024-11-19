import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth.auth import get_current_user, jwks
from auth.JWTBearer import JWTBearer
from crud.task import (create_task, delete_task, get_task_by_id,
                       get_task_by_status, get_task_by_user_id, update_task)
from crud.user import get_user_by_username
from db.database import get_db
from models.task import Task as TaskModel
from schemas.task import TaskCreate, TaskInDB, TaskUpdate

router = APIRouter(prefix="/api", tags=["Tasks"])

auth = JWTBearer(jwks)

@router.post("/tasks", response_model=TaskInDB, dependencies=[Depends(auth)], status_code=201)
async def create_new_task(task: TaskCreate, user_username=Depends(get_current_user), db: Session = Depends(get_db)):
    user = get_user_by_username(user_username, db)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return create_task(task, user.id, db)

@router.get("/tasks", response_model=List[TaskInDB], dependencies=[Depends(auth)])
async def get_tasks(user_username=Depends(get_current_user), db: Session = Depends(get_db)):
    user = get_user_by_username(user_username, db)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return get_task_by_user_id(user.id, db)

@router.get("/tasks/{task_id}", response_model=TaskInDB, dependencies=[Depends(auth)])
async def get_task(task_id: str, db: Session = Depends(get_db)):
    return get_task_by_id(task_id, db)

# get tasks by status
@router.get("/tasks/status/{status}", response_model=List[TaskInDB], dependencies=[Depends(auth)])
async def get_tasks_by_status(status: str, db: Session = Depends(get_db)):
    tasks = get_task_by_status(status, db)
    return tasks

@router.put("/tasks/{task_id}", response_model=TaskInDB, dependencies=[Depends(auth)])
async def update_task_by_id(task_id: str, task: TaskUpdate, db: Session = Depends(get_db)):
    try:   
        return update_task(task_id, task, db)

    except Exception as exc:
        logging.exception("Unexpected error updating task: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while updating the task.") from exc
    
@router.delete("/tasks/{task_id}", dependencies=[Depends(auth)], status_code=204)
async def delete_task_by_id(task_id: str, db: Session = Depends(get_db)):
    
    delete_task(task_id, db)

    return None
