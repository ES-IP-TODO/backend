import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.mysql import MySqlContainer

from crud.task import create_task, get_task_by_id, get_task_by_user_id
from db.database import get_db
from main import app
from models.task import Task as TaskModel
from models.task import TaskPriority, TaskStatus
from models.user import User as UserModel
from schemas.task import TaskCreate

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
    UserModel.metadata.create_all(engine)

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

@pytest.fixture(name="new_user", scope="module")
def create_test_user(test_db):
    new_user = UserModel(
        id="test_id",
        given_name="Test",
        family_name="User",
        username="test_user",
        email="email",
    )
    test_db.add(new_user)
    test_db.commit()
    yield new_user

    test_db.query(TaskModel).filter(TaskModel.user_id == new_user.id).delete()
    test_db.delete(new_user)
    test_db.commit()

def test_create_task(test_db, new_user: UserModel):
    new_task = TaskCreate(
        title="Test Task",
        description="Test Description",
        priority="low",
        deadline=datetime.now(timezone.utc) + timedelta(days=3),
    )

    task = create_task(new_task, new_user.id, test_db)

    assert task is not None
    assert task.title == new_task.title
    assert task.description == new_task.description
    assert task.priority == TaskPriority.LOW
    assert abs((task.deadline.replace(tzinfo=timezone.utc) - new_task.deadline).total_seconds()) < 2
    assert task.user_id == new_user.id
    assert task.status == TaskStatus.TODO
    assert task.created_at is not None

def test_create_task_exception(test_db, new_user: UserModel):
    new_task = TaskCreate(
        title="Test Task",
        description="Test Description",
        priority="low",
        deadline=datetime.now(timezone.utc) + timedelta(days=3),
    )

    with pytest.raises(HTTPException) as exc_info:
        with patch.object(Session, 'add', side_effect=SQLAlchemyError):
            create_task(new_task, new_user.id, test_db)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "An error occurred while creating the task."



