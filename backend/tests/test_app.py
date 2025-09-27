import datetime
import os
import runpy
import sys
from unittest.mock import MagicMock, patch

import jwt
import pytest
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app import app
from models import Connection, ConnectionRequest, Notification, Post, User

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_jwt_decode():
    with patch("jwt.decode") as mock_decode:
        mock_decode.return_value = {"user_id": 1}
        yield mock_decode


def test_token_required_missing_token(client):
    response = client.get("/users/me")
    assert response.status_code == 401
    assert response.json["message"] == "Token is missing!"


@patch("jwt.decode")
def test_token_required_invalid_token(mock_decode, client):
    mock_decode.side_effect = jwt.InvalidTokenError
    response = client.get("/users/me", headers={"x-access-token": "invalid_token"})
    assert response.status_code == 401
    assert response.json["message"] == "Token is invalid!"


@patch("app.session.add")
@patch("app.session.commit")
@patch("app.session.query")
def test_register_user_success(mock_query, mock_commit, mock_add, client):
    # Mock: no existing user
    mock_query.return_value.filter_by.return_value.first.return_value = None

    response = client.post(
        "/auth/register",
        json={"email": "newuser@example.com", "password": "securepass123"},
    )

    assert response.status_code == 201
    data = response.json
    assert "user_id" in data
    assert data["message"] == "User registered successfully"

    # Ensure session.add and commit were called
    mock_add.assert_called()
    mock_commit.assert_called()


@patch("app.session.query")
def test_register_user_email_exists(mock_query, client):
    mock_query.return_value.filter_by.return_value.first.return_value = User(
        email="existing@example.com"
    )
    response = client.post(
        "/auth/register",
        json={"email": "existing@example.com", "password": "password123"},
    )
    assert response.status_code == 409


@patch("app.session.query")
def test_get_user_profile_not_found(mock_query, client, mock_jwt_decode):
    # mock current_user to pass token_required decorator
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.side_effect = [
        MagicMock(
            first=MagicMock(return_value=mock_current_user)
        ),  # current_user lookup
        MagicMock(first=MagicMock(return_value=None)),  # requested user not found
    ]

    response = client.get(
        "/users/999/profile", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 404
    data = response.json
    assert data["message"] == "User not found"


def test_register_user_missing_fields(client):
    response = client.post("/auth/register", json={"email": "test@example.com"})
    assert response.status_code == 400


@patch("app.session.query")
def test_login_user_success(mock_query, client):
    mock_user = User(
        id=1,
        email="test@example.com",
        password_hash=generate_password_hash("password123"),
    )
    mock_query.return_value.filter_by.return_value.first.return_value = mock_user

    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    data = response.json
    # Check that the response contains the correct keys for login
    assert "message" in data
    assert data["message"] == "Login successful"
    assert "token" in data


@patch("app.session.query")
def test_login_user_invalid_credentials(mock_query, client):
    mock_query.return_value.filter_by.return_value.first.return_value = None
    response = client.post(
        "/auth/login", json={"email": "test@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


@patch("app.session.query")
def test_login_user_wrong_password(mock_query, client):
    mock_user = User(
        id=1,
        email="test@example.com",
        password_hash=generate_password_hash("password123"),
    )
    mock_query.return_value.filter_by.return_value.first.return_value = mock_user
    response = client.post(
        "/auth/login", json={"email": "test@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


@patch("app.session.query")
def test_get_current_user_success(mock_query, client, mock_jwt_decode):
    mock_user = User(id=1, email="current@example.com", display_name="Current User")
    mock_query.return_value.filter_by.return_value.first.return_value = mock_user
    response = client.get("/users/me", headers={"x-access-token": "valid_token"})
    assert response.status_code == 200
    assert response.json["email"] == "current@example.com"


@patch("app.session.query")
def test_search_users_no_query(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    response = client.get("/users/search", headers={"x-access-token": "valid_token"})
    assert response.status_code == 200
    assert response.json == []


@patch("app.session.query")
def test_search_users_no_results(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    mock_query.return_value.filter.return_value.all.return_value = []
    response = client.get(
        "/users/search?query=nonexistent",
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 200
    assert response.json == []


@patch("app.session.query")
def test_search_users_with_connections_and_pending_requests(
    mock_query, client, mock_jwt_decode
):
    mock_current_user = User(id=1)
    mock_user2 = User(id=2, display_name="user2")
    mock_user3 = User(id=3, display_name="user3")
    mock_connection = Connection(user_id1=1, user_id2=2)
    mock_request = ConnectionRequest(from_user_id=3, to_user_id=1, status="pending")
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    mock_query.return_value.filter.return_value.all.side_effect = [
        [mock_user2, mock_user3],
        [mock_connection],
        [mock_request],
    ]
    response = client.get(
        "/users/search?query=user", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 200
    assert len(response.json) == 2
    assert response.json[0]["is_connection"] is True
    assert response.json[1]["has_pending_request"] is True


@patch("app.session.query")
def test_request_connection_to_self(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    response = client.post(
        "/connections/request",
        json={"to_user_id": 1},
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 400


@patch("app.session.query")
def test_request_connection_missing_to_user_id(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    response = client.post(
        "/connections/request",
        json={},
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 400


@patch("app.session.query")
def test_request_connection_already_exists(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_connection = Connection(user_id1=1, user_id2=2)
    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)),
        MagicMock(first=MagicMock(return_value=mock_connection)),
    ]
    response = client.post(
        "/connections/request",
        json={"to_user_id": 2},
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 409


@patch("app.session.add")
@patch("app.session.commit")
@patch("app.session.query")
def test_request_connection_integrity_error(
    mock_query, mock_commit, mock_add, client, mock_jwt_decode
):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)),
        MagicMock(first=MagicMock(return_value=None)),
    ]
    mock_add.side_effect = IntegrityError(None, None, None)
    response = client.post(
        "/connections/request",
        json={"to_user_id": 2},
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 409


@patch("app.session.add")
@patch("app.session.query")
def test_request_connection_exception(mock_query, mock_add, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)),
        MagicMock(first=MagicMock(return_value=None)),
    ]
    mock_add.side_effect = Exception("Test Exception")
    response = client.post(
        "/connections/request",
        json={"to_user_id": 2},
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 500


@patch("app.session.query")
def test_accept_connection_missing_request_id(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    # Configure mock_query to return different mocks for subsequent calls
    mock_query.side_effect = [
        MagicMock(
            return_value=MagicMock(
                filter_by=MagicMock(
                    return_value=MagicMock(
                        first=MagicMock(return_value=mock_current_user)
                    )
                )
            )
        ),  # First call: session.query(User)
        MagicMock(
            return_value=MagicMock(
                filter_by=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=None))
                )
            )
        ),  # Second call: session.query(ConnectionRequest) - this won't be reached due to early exit
    ]
    response = client.post(
        "/connections/accept",
        json={},
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 400
    assert response.json["message"] == "request_id is required"


@patch("app.session.query")
def test_accept_connection_request_not_found(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    # Create a mock for the ConnectionRequest query that returns None
    mock_connection_request_query = MagicMock()
    mock_connection_request_query.filter_by.return_value.first.return_value = None

    # Configure mock_query to return the mock_current_user for the first call (User)  # For User query in token_required
    # and the mock_connection_request_query for the second call (ConnectionRequest)  # For ConnectionRequest query in accept_connection
    mock_query.side_effect = [
        MagicMock(
            return_value=MagicMock(
                filter_by=MagicMock(
                    return_value=MagicMock(
                        first=MagicMock(return_value=mock_current_user)
                    )
                )
            )
        ),
        mock_connection_request_query,
    ]
    response = client.post(
        "/connections/accept",
        json={"request_id": 999},
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 404
    assert response.json["message"] == "Pending connection request not found"


@patch("app.session.query")
def test_deny_connection_missing_request_id(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    response = client.post(
        "/connections/deny", json={}, headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 400


@patch("app.session.query")
def test_deny_connection_request_not_found(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)),
        MagicMock(first=MagicMock(return_value=None)),
    ]
    response = client.post(
        "/connections/deny",
        json={"request_id": 999},
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 404


@patch("app.session.commit")
@patch("app.session.query")
def test_deny_connection_exception(mock_query, mock_commit, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_request = ConnectionRequest(
        id=1, from_user_id=2, to_user_id=1, status="pending"
    )
    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)),
        MagicMock(first=MagicMock(return_value=mock_request)),
    ]
    mock_commit.side_effect = Exception("Test Exception")
    response = client.post(
        "/connections/deny",
        json={"request_id": 1},
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 500


@patch("app.session.query")
def test_get_user_connections_unauthorized(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    response = client.get(
        "/users/2/connections", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 403


@patch("app.session.query")
def test_get_user_connections_no_connections(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    mock_query.return_value.filter.return_value.all.return_value = []
    response = client.get(
        "/users/1/connections", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 200
    assert response.json == []


@patch("app.session.query")
def test_get_user_connections_with_connections(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_user2 = User(id=2, display_name="user2")
    mock_connection = Connection(user_id1=2, user_id2=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    mock_query.return_value.filter.return_value.all.return_value = [mock_connection]
    mock_query.return_value.filter_by.return_value.first.side_effect = [
        mock_current_user,
        mock_user2,
    ]
    response = client.get(
        "/users/1/connections", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 200
    assert len(response.json) == 1


@patch("app.session.query")
def test_get_pending_requests_unauthorized(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    response = client.get(
        "/users/2/pending_requests", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 403


@patch("app.session.query")
def test_get_pending_requests_no_requests(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    mock_query.return_value.filter_by.return_value.all.return_value = []
    response = client.get(
        "/users/1/pending_requests", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 200
    assert response.json == []


@patch("app.session.query")
def test_get_pending_requests_with_requests(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_user2 = User(id=2, display_name="user2")
    mock_request = ConnectionRequest(
        id=1,
        from_user_id=2,
        to_user_id=1,
        status="pending",
        created_at=datetime.datetime.utcnow(),
    )
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    mock_query.return_value.filter_by.return_value.all.return_value = [mock_request]
    mock_query.return_value.filter_by.return_value.first.side_effect = [
        mock_current_user,
        mock_user2,
    ]
    response = client.get(
        "/users/1/pending_requests", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 200
    assert len(response.json) == 1


@patch("app.session.query")
def test_get_sent_requests_unauthorized(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    response = client.get(
        "/users/2/sent_requests", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 403


@patch("app.session.query")
def test_get_sent_requests_no_requests(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    mock_query.return_value.filter_by.return_value.all.return_value = []
    response = client.get(
        "/users/1/sent_requests", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 200
    assert response.json == []


@patch("app.session.query")
def test_get_sent_requests_with_requests(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_user2 = User(id=2, display_name="user2")
    mock_request = ConnectionRequest(
        id=1,
        from_user_id=1,
        to_user_id=2,
        status="pending",
        created_at=datetime.datetime.utcnow(),
    )
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    mock_query.return_value.filter_by.return_value.all.return_value = [mock_request]
    mock_query.return_value.filter_by.return_value.first.side_effect = [
        mock_current_user,
        mock_user2,
    ]
    response = client.get(
        "/users/1/sent_requests", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 200
    assert len(response.json) == 1


@patch("app.session.query")
def test_get_user_posts_unauthorized(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    response = client.get("/users/2/posts", headers={"x-access-token": "valid_token"})
    assert response.status_code == 403


@patch("app.session.query")
def test_get_user_posts_no_posts(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    mock_query.return_value.filter_by.return_value.order_by.return_value.all.return_value = (
        []
    )
    response = client.get("/users/1/posts", headers={"x-access-token": "valid_token"})
    assert response.status_code == 200
    assert response.json == []


@patch("app.session.query")
def test_get_user_posts_with_posts(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1, display_name="test", profile_picture_url="test.jpg")
    mock_post = Post(
        id=1,
        caption="test post",
        image_url="test.jpg",
        created_at=datetime.datetime.utcnow(),
        user_id=1,
    )

    # Mock the sequence of queries: User lookup, Posts query, Like queries, Comment queries
    mock_user_query = MagicMock()
    mock_user_query.filter_by.return_value.first.return_value = mock_current_user

    mock_posts_query = MagicMock()
    mock_posts_query.filter_by.return_value.order_by.return_value.all.return_value = [
        mock_post
    ]

    mock_like_count_query = MagicMock()
    mock_like_count_query.filter_by.return_value.count.return_value = 0

    mock_like_check_query = MagicMock()
    mock_like_check_query.filter_by.return_value.first.return_value = None

    mock_comment_count_query = MagicMock()
    mock_comment_count_query.filter_by.return_value.count.return_value = 0

    mock_comment_query = MagicMock()
    mock_comment_query.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = (
        []
    )

    # Set up the side_effect to return different mock objects for different query calls
    mock_query.side_effect = [
        mock_user_query,
        mock_posts_query,
        mock_like_count_query,
        mock_like_check_query,
        mock_comment_count_query,
        mock_comment_query,
    ]

    response = client.get("/users/1/posts", headers={"x-access-token": "valid_token"})
    assert response.status_code == 200
    assert len(response.json) == 1


@patch("app.session.query")
def test_get_connections_posts_unauthorized(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    response = client.get(
        "/users/2/connections/posts", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 403


@patch("app.session.query")
def test_get_connections_posts_no_posts(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.return_value.first.return_value = (
        mock_current_user
    )
    mock_query.return_value.filter.return_value.all.return_value = []
    response = client.get(
        "/users/1/connections/posts", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 200
    assert response.json == []


@patch("app.session.query")
def test_get_connections_posts_with_posts(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1, display_name="test", profile_picture_url="test.jpg")
    mock_user2 = User(id=2, display_name="user2", profile_picture_url="user2.jpg")
    mock_connection = Connection(user_id1=1, user_id2=2)
    mock_post = Post(id=1, user_id=2, created_at=datetime.datetime.utcnow())

    # Mock the sequence of queries: User lookup, Connections query, Posts query, Post user lookup, Like queries, Comment queries
    mock_user_query = MagicMock()
    mock_user_query.filter_by.return_value.first.return_value = mock_current_user

    mock_connections_query = MagicMock()
    mock_connections_query.filter.return_value.all.return_value = [mock_connection]

    mock_posts_query = MagicMock()
    mock_posts_query.filter.return_value.order_by.return_value.all.return_value = [
        mock_post
    ]

    mock_post_user_query = MagicMock()
    mock_post_user_query.filter_by.return_value.first.return_value = mock_user2

    mock_like_count_query = MagicMock()
    mock_like_count_query.filter_by.return_value.count.return_value = 0

    mock_like_check_query = MagicMock()
    mock_like_check_query.filter_by.return_value.first.return_value = None

    mock_comment_count_query = MagicMock()
    mock_comment_count_query.filter_by.return_value.count.return_value = 0

    mock_comment_query = MagicMock()
    mock_comment_query.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = (
        []
    )

    # Set up the side_effect to return different mock objects for different query calls
    mock_query.side_effect = [
        mock_user_query,
        mock_connections_query,
        mock_posts_query,
        mock_post_user_query,
        mock_like_count_query,
        mock_like_check_query,
        mock_comment_count_query,
        mock_comment_query,
    ]

    response = client.get(
        "/users/1/connections/posts", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 200
    assert len(response.json) == 1


@patch("app.session.query")
def test_get_connections_posts_post_user_none(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_connection = Connection(user_id1=1, user_id2=2)
    mock_post = Post(id=1, user_id=2)
    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)),
        MagicMock(first=MagicMock(return_value=None)),
    ]
    mock_query.return_value.filter.return_value.all.return_value = [mock_connection]
    mock_query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        mock_post
    ]
    response = client.get(
        "/users/1/connections/posts", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 200
    assert response.json == []


# Test notification endpoints
@patch("app.session.query")
def test_get_notifications(mock_query, client, mock_jwt_decode):
    """Test getting notifications for a user."""
    mock_current_user = User(id=1)
    mock_notification = Notification(
        id=1,
        user_id=1,
        actor_user_id=2,
        type="post_liked",
        message="Test notification",
        target_url="/posts/1",
        is_read=False,
        created_at=datetime.now(),
    )

    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)),
    ]
    mock_query.return_value.filter_by.return_value.order_by.return_value.all.return_value = [
        mock_notification
    ]

    response = client.get("/notifications", headers={"x-access-token": "valid_token"})
    assert response.status_code == 200
    assert len(response.json) == 1


@patch("app.session.query")
def test_get_notifications_empty(mock_query, client, mock_jwt_decode):
    """Test getting notifications when none exist."""
    mock_current_user = User(id=1)
    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)),
    ]
    mock_query.return_value.filter_by.return_value.order_by.return_value.all.return_value = (
        []
    )

    response = client.get("/notifications", headers={"x-access-token": "valid_token"})
    assert response.status_code == 200
    assert response.json == []


@patch("app.session.query")
def test_mark_notification_read_success(mock_query, client, mock_jwt_decode):
    """Test marking a notification as read."""
    mock_current_user = User(id=1)
    mock_notification = Notification(
        id=1,
        user_id=1,
        actor_user_id=2,
        type="post_liked",
        message="Test notification",
        target_url="/posts/1",
        is_read=False,
    )

    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)),
        MagicMock(first=MagicMock(return_value=mock_notification)),
    ]

    response = client.post(
        "/notifications/1/mark-read", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 200
    assert mock_notification.is_read is True


@patch("app.session.query")
def test_mark_notification_read_not_found(mock_query, client, mock_jwt_decode):
    """Test marking a non-existent notification as read."""
    mock_current_user = User(id=1)

    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)),
        MagicMock(first=MagicMock(return_value=None)),
    ]

    response = client.post(
        "/notifications/999/mark-read", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 404


@patch("app.session.query")
def test_mark_notification_read_wrong_user(mock_query, client, mock_jwt_decode):
    """Test marking a notification that belongs to another user."""
    mock_current_user = User(id=1)
    mock_notification = Notification(
        id=1,
        user_id=2,  # Different user
        actor_user_id=3,
        type="post_liked",
        message="Test notification",
        target_url="/posts/1",
        is_read=False,
    )

    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)),
        MagicMock(first=MagicMock(return_value=mock_notification)),
    ]

    response = client.post(
        "/notifications/1/mark-read", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 403


@patch("app.session.query")
@patch("app.session.commit")
def test_mark_all_notifications_read(mock_commit, mock_query, client, mock_jwt_decode):
    """Test marking all notifications as read."""
    mock_current_user = User(id=1)
    mock_notifications = [
        Notification(id=1, user_id=1, is_read=False),
        Notification(id=2, user_id=1, is_read=False),
    ]

    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)),
        MagicMock(all=MagicMock(return_value=mock_notifications)),
    ]

    response = client.post(
        "/notifications/mark-all-read", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 200
    assert response.json["count"] == 2

    # Verify all notifications were marked as read
    for notification in mock_notifications:
        assert notification.is_read is True


@patch("app.session.query")
def test_create_notification_all_types(mock_query, client, mock_jwt_decode):
    """Test create_notification function with all notification types."""
    from app import create_notification

    mock_user = User(id=1, display_name="Test User")
    mock_query.return_value.filter_by.return_value.first.return_value = mock_user

    # Test each notification type
    notification_types = [
        ("post_liked", 1),
        ("post_commented", 1),
        ("connection_request", None),
        ("connection_accepted", None),
    ]

    for notif_type, post_id in notification_types:
        create_notification(1, 2, notif_type, post_id)
        # Function should not raise exceptions


@patch("app.session.query")
def test_create_notification_unknown_type(mock_query, client, mock_jwt_decode):
    """Test create_notification with unknown notification type."""
    from app import create_notification

    mock_user = User(id=1, display_name="Test User")
    mock_query.return_value.filter_by.return_value.first.return_value = mock_user

    # Should not create notification for unknown type
    create_notification(1, 2, "unknown_type", None)
    # Function should handle gracefully without error


@patch("app.session.query")
def test_create_notification_missing_actor(mock_query, client, mock_jwt_decode):
    """Test create_notification with missing actor user."""
    from app import create_notification

    mock_query.return_value.filter_by.return_value.first.return_value = None

    # Should not create notification when actor doesn't exist
    create_notification(1, 999, "post_liked", 1)
    # Function should handle gracefully without error


@patch("flask.app.Flask.run")
@patch.dict("os.environ", {"FLASK_HOST": "0.0.0.0"}, clear=False)
def test_main(mock_run):
    runpy.run_module("app", run_name="__main__")
    mock_run.assert_called_with(host="0.0.0.0", port=5000)
