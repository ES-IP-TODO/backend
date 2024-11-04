import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.mysql import MySqlContainer

from crud.task import (create_task, delete_task, get_task_by_id,
                       get_task_by_status, get_task_by_user_id, update_task)
from crud.user import create_user, get_user_by_email, get_user_by_username
from db.database import get_db
from main import app
from models.task import Task as TaskModel
from models.task import TaskPriority, TaskStatus
from models.user import User
from models.user import User as UserModel
from schemas.task import TaskCreate, TaskUpdate
from schemas.user import CreateUser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

my_sql_container = MySqlContainer(
    "mysql:8.0",
    root_password="test_root_password",
    dbname="test_db",
    username="test_username",
    password="test_password",
)


@pytest.fixture(name="session", scope="module")
def setup():
    # Start the MySQL container
    my_sql_container.start()
    connection_url = my_sql_container.get_connection_url()
    print(connection_url)
    engine = create_engine(connection_url, connect_args={})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    User.metadata.create_all(engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    logger.info("running setup")
    yield SessionLocal
    logger.info("ending setup")
    my_sql_container.stop()


@pytest.fixture(name="test_db", scope="module")
def create_test_db(session):
    db = session()
    logger.info("creating test db")
    yield db
    logger.info("closing test db")
    db.close()


@pytest.fixture(name="test_user", scope="function")
def create_test_user(test_db):
    test_user = User(
        id="id1",
        given_name="given_name1",
        family_name="family_name1",
        username="username1",
        email="email1",
    )
    test_db.add(test_user)
    test_db.commit()
    logger.info("creating test user")
    yield test_user
    logger.info("deleting test user")
    test_db.query(TaskModel).filter(TaskModel.user_id == test_user.id).delete()
    test_db.delete(test_user)
    test_db.commit()


def test_get_user_by_username_found(test_db, test_user):
    found_user = get_user_by_username(test_user.username, test_db)
    assert found_user is not None
    assert found_user.id == "id1"


def test_get_user_by_username_not_found(test_db):
    with pytest.raises(HTTPException) as exc_info:
        get_user_by_username("not_exist", test_db)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"

def test_get_user_by_email_found(test_db, test_user):
    found_user = get_user_by_email(test_user.email, test_db)
    assert found_user is not None
    assert found_user.id == "id1"

def test_get_user_by_email_not_found(test_db):
    with pytest.raises(HTTPException) as exc_info:
        get_user_by_email("not_exist", test_db)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


def test_create_user(test_db):
    user_data = CreateUser(
        id="id2",
        given_name="given_name2",
        family_name="family_name2",
        username="username2",
        email="email2",
    )
    user = create_user(user_data, test_db)
    assert user is not None
    assert user == test_db.query(User).filter(User.username == "username2").first()
    assert (
        user.id == "id2"
        and user.given_name == "given_name2"
        and user.username == "username2"
        and user.family_name == "family_name2"
        and user.email == "email2"
    )

def test_create_task(test_db, test_user: UserModel):
    new_task = TaskCreate(
        title="Test Task",
        description="Test Description",
        priority="low",
        deadline=datetime.now(timezone.utc) + timedelta(days=3),
    )

    task = create_task(new_task, test_user.id, test_db)

    assert task is not None
    assert task.title == new_task.title
    assert task.description == new_task.description
    assert task.priority == TaskPriority.LOW
    assert abs((task.deadline.replace(tzinfo=timezone.utc) - new_task.deadline).total_seconds()) < 2
    assert task.user_id == test_user.id
    assert task.status == TaskStatus.TODO
    assert task.created_at is not None

def test_create_task_exception(test_db, test_user: UserModel):
    new_task = TaskCreate(
        title="Test Task",
        description="Test Description",
        priority="low",
        deadline=datetime.now(timezone.utc) + timedelta(days=3),
    )

    with pytest.raises(HTTPException) as exc_info:
        with patch.object(Session, 'add', side_effect=SQLAlchemyError):
            create_task(new_task, test_user.id, test_db)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "An error occurred while creating the task."

def test_get_task_by_status(test_db, test_user: UserModel):
    new_task = TaskCreate(
        title="Test Task",
        description="Test Description",
        priority="low",
        deadline=datetime.now(timezone.utc) + timedelta(days=3),
    )

    task = create_task(new_task, test_user.id, test_db)
    tasks = get_task_by_status("todo", test_db)
    assert tasks is not None
    assert len(tasks) == 1
    assert tasks[0] == task

def test_update_task(test_db, test_user: UserModel):
    new_task = TaskCreate(
        title="Test Task",
        description="Test Description",
        priority="low",
        deadline=datetime.now(timezone.utc) + timedelta(days=3),
    )

    task = create_task(new_task, test_user.id, test_db)

    updated_task = TaskUpdate(
        title="Updated Task",
        description="Updated Description",
        priority="high",
        deadline=datetime.now(timezone.utc) + timedelta(days=5),
    )

    updated_task = update_task(task.id, updated_task, test_db)
    assert updated_task is not None
    assert updated_task.title == "Updated Task"
    assert updated_task.description == "Updated Description"
    assert updated_task.priority == TaskPriority.HIGH
    assert updated_task.user_id == test_user.id
    assert updated_task.status == TaskStatus.TODO
    assert updated_task.created_at is not None

def test_delete_task(test_db, test_user: UserModel):
    new_task = TaskCreate(
        title="Test Task",
        description="Test Description",
        priority="low",
        deadline=datetime.now(timezone.utc) + timedelta(days=3),
    )

    task = create_task(new_task, test_user.id, test_db)
    delete_task(task.id, test_db)
    assert test_db.query(TaskModel).filter(TaskModel.id == task.id).first() is None