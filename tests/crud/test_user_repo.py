import logging
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.mysql import MySqlContainer

from crud.user import create_user, get_user_by_email, get_user_by_username
from db.database import get_db
from main import app
from models.user import User
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
