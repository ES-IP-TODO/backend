import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth.auth import get_current_user
from auth.JWTBearer import JWTAuthorizationCredentials, JWTBearer
from db.database import get_db
from main import app
from models.task import TaskPriority, TaskStatus
from routers.task import auth
from schemas.task import TaskCreate, TaskInDB

client = TestClient(app)

credentials = JWTAuthorizationCredentials(
    jwt_token="token",
    header={"kid": "some_kid"},
    claims={"sub": "user_id"},
    signature="signature",
    message="message",
)

@pytest.fixture(scope="module")
def mock_db():
    db = MagicMock(spec=Session)
    app.dependency_overrides[get_db] = lambda: db
    yield db

@pytest.fixture(autouse=True)
def reset_mock_db(mock_db):
    mock_db.reset_mock()

@patch("routers.task.get_user_by_username")
@patch("routers.task.create_task")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_create_new_task(mock_jwt_bearer, mock_create_task, mock_get_user_by_username, mock_db):
    app.dependency_overrides[auth] = lambda: credentials
    app.dependency_overrides[get_current_user] = lambda: "username1"

    headers = {"Authorization": "Bearer token"}

    task_data = {
        "title": "Test Task",
        "description": "Test Description",
        "priority": "low",
        "deadline": (datetime.now() + timedelta(days=1)).isoformat()
    }

    mock_get_user_by_username.return_value = MagicMock(id="user_id")

    mock_create_task.return_value = TaskInDB(
        **task_data,
        created_at=datetime.now(),
        id="task_id",
        user_id="user_id",
        status=TaskStatus.TODO,
    )

    response = client.post("/tasks", json=task_data, headers=headers)

    print(response.json())

    assert response.status_code == 201
    assert response.json()["title"] == task_data["title"]
    assert response.json()["description"] == task_data["description"]
    assert response.json()["priority"] == "low"
    assert response.json()["status"] == "todo"
    assert response.json()["deadline"] == task_data["deadline"]
    assert response.json()["user_id"] == "user_id"
    assert response.json()["id"] == "task_id"
    assert response.json()["created_at"] is not None


@patch("routers.task.get_user_by_username")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_create_new_task_user_not_found(mock_jwt_bearer, mock_get_user_by_username, mock_db):
    app.dependency_overrides[auth] = lambda: credentials
    app.dependency_overrides[get_current_user] = lambda: "username1"

    headers = {"Authorization": "Bearer token"}

    mock_get_user_by_username.return_value = None

    response = client.get("/tasks", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

@patch("routers.task.get_user_by_username")
@patch("routers.task.get_task_by_user_id")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_tasks(mock_jwt_bearer, mock_get_task_by_user_id, mock_get_user_by_username, mock_db):
    app.dependency_overrides[auth] = lambda: credentials
    app.dependency_overrides[get_current_user] = lambda: "username1"

    headers = {"Authorization": "Bearer token"}

    mock_get_user_by_username.return_value = MagicMock(id="user_id")

    mock_get_task_by_user_id.return_value = [
        TaskInDB(
            title="Test Task",
            description="Test Description",
            priority="low",
            deadline=(datetime.now() + timedelta(days=1)).isoformat(),
            created_at=datetime.now(),
            id="task_id",
            user_id="user_id",
            status=TaskStatus.TODO,
        )
    ]

    response = client.get("/tasks", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1

    task = response.json()[0]
    assert task["title"] == "Test Task"
    assert task["description"] == "Test Description"
    assert task["priority"] == "low"
    assert task["status"] == "todo"
    assert task["deadline"] is not None
    assert task["user_id"] == "user_id"
    assert task["id"] == "task_id"
    assert task["created_at"] is not None

# test get_tasks with no user found
@patch("routers.task.get_user_by_username")
@patch("routers.task.get_task_by_user_id")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_tasks_user_not_found(mock_jwt_bearer, mock_get_task_by_user_id, mock_get_user_by_username, mock_db):
    app.dependency_overrides[auth] = lambda: credentials
    app.dependency_overrides[get_current_user] = lambda: "username1"

    headers = {"Authorization": "Bearer token"}

    mock_get_user_by_username.return_value = None

    response = client.get("/tasks", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

@patch("routers.task.get_user_by_username")
@patch("routers.task.get_task_by_id")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_task(mock_jwt_bearer, mock_get_task_by_id, mock_get_user_by_username, mock_db):
    app.dependency_overrides[auth] = lambda: credentials
    app.dependency_overrides[get_current_user] = lambda: "username1"

    headers = {"Authorization": "Bearer token"}

    mock_get_task_by_id.return_value = TaskInDB(
        title="Test Task",
        description="Test Description",
        priority="low",
        deadline=(datetime.now() + timedelta(days=1)).isoformat(),
        created_at=datetime.now(),
        id="task_id",
        user_id="user_id",
        status=TaskStatus.TODO,
    )

    response = client.get("/tasks/task_id", headers=headers)

    assert response.status_code == 200
    assert response.json()["title"] == "Test Task"
    assert response.json()["description"] == "Test Description"
    assert response.json()["priority"] == "low"
    assert response.json()["status"] == "todo"
    assert response.json()["deadline"] is not None
    assert response.json()["user_id"] == "user_id"
    assert response.json()["id"] == "task_id"
    assert response.json()["created_at"] is not None

# test get_task with no task found
@patch("routers.task.get_task_by_id")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_task_not_found(mock_jwt_bearer, mock_get_task_by_id, mock_db):
    app.dependency_overrides[auth] = lambda: credentials
    app.dependency_overrides[get_current_user] = lambda: "username1"

    headers = {"Authorization": "Bearer token"}

    mock_get_task_by_id.side_effect = HTTPException(status_code=404, detail="Task not found")

    response = client.get("/tasks/task_id", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

# test get_tasks_by_status
@patch("routers.task.get_task_by_status")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_tasks_by_status(mock_jwt_bearer, mock_get_task_by_status, mock_db):
    app.dependency_overrides[auth] = lambda: credentials
    app.dependency_overrides[get_current_user] = lambda: "username1"

    headers = {"Authorization": "Bearer token"}

    mock_get_task_by_status.return_value = [
        TaskInDB(
            title="Test Task",
            description="Test Description",
            priority="low",
            deadline=(datetime.now() + timedelta(days=1)).isoformat(),
            created_at=datetime.now(),
            id="task_id",
            user_id="user_id",
            status=TaskStatus.TODO,
        )
    ]

    response = client.get("/tasks/status/todo", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1

    task = response.json()[0]
    assert task["title"] == "Test Task"
    assert task["description"] == "Test Description"
    assert task["priority"] == "low"
    assert task["status"] == "todo"
    assert task["deadline"] is not None
    assert task["user_id"] == "user_id"
    assert task["id"] == "task_id"
    assert task["created_at"] is not None

# test update_task
@patch("routers.task.update_task")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_update_task(mock_jwt_bearer, mock_update_task, mock_db):
    app.dependency_overrides[auth] = lambda: credentials
    app.dependency_overrides[get_current_user] = lambda: "username1"

    headers = {"Authorization": "Bearer token"}

    task_data = {
        "title": "Test Task",
        "description": "Test Description",
        "priority": "low",
        "deadline": (datetime.now() + timedelta(days=1)).isoformat()
    }

    mock_update_task.return_value = TaskInDB(
        **task_data,
        created_at=datetime.now(),
        id="task_id",
        user_id="user_id",
        status=TaskStatus.TODO,
    )

    response = client.put("/tasks/task_id", json=task_data, headers=headers)

    assert response.status_code == 200
    assert response.json()["title"] == task_data["title"]
    assert response.json()["description"] == task_data["description"]
    assert response.json()["priority"] == "low"
    assert response.json()["status"] == "todo"
    assert response.json()["deadline"] == task_data["deadline"]
    assert response.json()["user_id"] == "user_id"
    assert response.json()["id"] == "task_id"
    assert response.json()["created_at"] is not None

@patch("routers.task.delete_task")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_delete_task(mock_jwt_bearer, mock_delete_task, mock_db):
    app.dependency_overrides[auth] = lambda: credentials
    app.dependency_overrides[get_current_user] = lambda: "username1"

    headers = {"Authorization": "Bearer token"}

    response = client.delete("/tasks/task_id", headers=headers)

    assert response.status_code == 204