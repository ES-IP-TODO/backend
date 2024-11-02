import os
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth.JWTBearer import JWTAuthorizationCredentials
from db.database import get_db
from main import app
from routers.user import auth
from schemas.user import CreateUser

load_dotenv()
REDIRECT_URI = os.environ.get("REDIRECT_URI")

client = TestClient(app)


@pytest.fixture(scope="module")
def mock_db():
    db = MagicMock(spec=Session)
    app.dependency_overrides[get_db] = lambda: db
    yield db


user_attributes = {
    "UserAttributes": [
        {"Name": "email", "Value": "email@email.com"},
        {"Name": "email_verified", "Value": "..."},
        {"Name": "family_name", "Value": "family_name1"},
        {"Name": "given_name", "Value": "given_name1"},
        {"Name": "sub", "Value": "id1"},
    ],
    "Username": "username1",
}


@pytest.fixture(autouse=True)
def reset_mock_db(mock_db):
    mock_db.reset_mock()


@patch("routers.user.create_user")
@patch("routers.user.user_info_with_token")
@patch("routers.user.auth_with_code", return_value=None)
def test_unsuccessful_login_with_invalid_credentials(
    mock_auth_with_code, mock_user_info_with_token, mock_create_user, mock_db
):
    response = client.post("/auth/sign-in?code=invalid_code")

    assert response.status_code == 401
    mock_auth_with_code.assert_called_once_with("invalid_code", REDIRECT_URI)
    assert mock_user_info_with_token.call_count == 0
    assert mock_db.query.call_count == 0
    assert mock_create_user.call_count == 0


@patch("routers.user.create_user")
@patch("routers.user.user_info_with_token", return_value=user_attributes)
@patch(
    "routers.user.auth_with_code",
    return_value={"token": "valid_token", "expires_in": 100},
)
def test_successful_login_with_valid_credentials_found_username(
    mock_auth_with_code, mock_user_info_with_token, mock_create_user, mock_db
):
    mock_db.query.return_value.filter.return_value.first.side_effect = [True, False]

    response = client.post("/auth/sign-in?code=valid_code")

    assert response.status_code == 200
    assert response.json() == {"token": "valid_token", "expires_in": 100}
    mock_auth_with_code.assert_called_once_with("valid_code", REDIRECT_URI)
    mock_user_info_with_token.assert_called_once_with("valid_token")
    assert mock_db.query.call_count == 1
    assert mock_create_user.call_count == 0


@patch("routers.user.create_user")
@patch("routers.user.user_info_with_token", return_value=user_attributes)
@patch(
    "routers.user.auth_with_code",
    return_value={"token": "valid_token", "expires_in": 100},
)
def test_successful_login_with_valid_credentials_found_email(
    mock_auth_with_code, mock_user_info_with_token, mock_create_user, mock_db
):
    mock_db.query.return_value.filter.return_value.first.side_effect = [False, True]

    response = client.post("/auth/sign-in?code=valid_code")

    assert response.status_code == 200
    assert response.json() == {"token": "valid_token", "expires_in": 100}
    mock_auth_with_code.assert_called_once_with("valid_code", REDIRECT_URI)
    mock_user_info_with_token.assert_called_once_with("valid_token")
    assert mock_db.query.call_count == 2
    assert mock_create_user.call_count == 0


@patch("routers.user.create_user")
@patch("routers.user.user_info_with_token", return_value=user_attributes)
@patch(
    "routers.user.auth_with_code",
    return_value={"token": "valid_token", "expires_in": 100},
)
def test_successful_login_with_valid_credentials_new_user(
    mock_auth_with_code, mock_user_info_with_token, mock_create_user, mock_db
):
    mock_db.query.return_value.filter.return_value.first.side_effect = [False, False]

    response = client.post("/auth/sign-in?code=valid_code")

    assert response.status_code == 200
    assert response.json() == {"token": "valid_token", "expires_in": 100}
    mock_auth_with_code.assert_called_once_with("valid_code", REDIRECT_URI)
    mock_user_info_with_token.assert_called_once_with("valid_token")
    assert mock_db.query.call_count == 2
    mock_create_user.assert_called_once_with(
        CreateUser(
            id=user_attributes["UserAttributes"][4]["Value"],
            given_name=user_attributes["UserAttributes"][3]["Value"],
            family_name=user_attributes["UserAttributes"][2]["Value"],
            username=user_attributes["Username"],
            email=user_attributes["UserAttributes"][0]["Value"],
        ),
        mock_db,
    )

@patch("routers.user.logout_with_token", return_value=True)
def test_successful_logout(mock_logout_with_token):
    app.dependency_overrides[auth] = lambda: JWTAuthorizationCredentials(
        jwt_token="token",
        header={"kid": "some_kid"},
        claims={"sub": "user_id"},
        signature="signature",
        message="message",
    )

    headers = {"Authorization": "Bearer token"}
    response = client.get("/auth/logout", headers=headers)

    assert response.status_code == 200
    assert response.json() == "Logout successful"

    mock_logout_with_token.assert_called_once_with("token")

    app.dependency_overrides = {}


@patch("routers.user.logout_with_token", return_value=False)
def test_unsuccessful_logout(mock_logout_with_token):
    app.dependency_overrides[auth] = lambda: JWTAuthorizationCredentials(
        jwt_token="token",
        header={"kid": "some_kid"},
        claims={"sub": "user_id"},
        signature="signature",
        message="message",
    )

    headers = {"Authorization": "Bearer token"}
    response = client.get("/auth/logout", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Error loging out..."}

    mock_logout_with_token.assert_called_once_with("token")

    app.dependency_overrides = {}