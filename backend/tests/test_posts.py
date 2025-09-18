import os
import sys
from unittest.mock import MagicMock, patch

import jwt
import pytest
from app import allowed_file, app
from models import Post, User
from werkzeug.datastructures import FileStorage

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)


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


@pytest.fixture
def mock_current_user():
    user = User(id=1, email="test@example.com", display_name="Test User")
    with patch("app.session.query") as mock_query:
        mock_query.return_value.filter_by.return_value.first.return_value = (
            user
        )
        yield user


def test_allowed_file_valid_extensions():
    assert allowed_file("image.png") is True
    assert allowed_file("document.jpg") is True
    assert allowed_file("photo.jpeg") is True
    assert allowed_file("animation.gif") is True
    assert allowed_file("picture.heic") is True
    assert allowed_file("web_image.webp") is True


def test_allowed_file_invalid_extensions():
    assert allowed_file("document.txt") is False
    assert allowed_file("archive.zip") is False
    assert allowed_file("script.py") is False
    assert allowed_file("noextension") is False
    assert allowed_file(".hiddenfile") is False


def test_upload_file_no_file_part(client, mock_jwt_decode, mock_current_user):
    response = client.post(
        "/posts/upload", headers={"x-access-token": "valid_token"}
    )
    assert response.status_code == 400
    assert response.json["message"] == "No file part"


def test_upload_file_no_selected_file(
    client, mock_jwt_decode, mock_current_user
):
    data = {"file": (FileStorage(stream=None, filename=""), "file")}
    response = client.post(
        "/posts/upload",
        data=data,
        content_type="multipart/form-data",
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 400
    assert response.json["message"] == "No selected file"


def test_upload_file_invalid_file_type(
    client, mock_jwt_decode, mock_current_user
):
    import io

    data = {
        "file": (
            FileStorage(
                stream=io.BytesIO(b"dummy content"), filename="test.txt"
            ),
            "file",
        )
    }
    response = client.post(
        "/posts/upload",
        data=data,
        content_type="multipart/form-data",
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 400
    assert response.json["message"] == "File type not allowed"


@patch("app.secure_filename", return_value="test_image.png")
@patch("os.path.join", return_value="/tmp/test_image.png")
def test_upload_file_success(
    mock_join,
    mock_secure_filename,
    client,
    mock_jwt_decode,
    mock_current_user,
):
    import io

    data = {"file": (io.BytesIO(b"dummy image data"), "test_image.png")}
    response = client.post(
        "/posts/upload",
        data=data,
        content_type="multipart/form-data",
        headers={"x-access-token": "valid_token"},
    )

    assert response.status_code == 200
    assert response.json["message"] == "File uploaded successfully"
    assert response.json["filename"] == "test_image.png"


def test_create_post_missing_fields(
    client, mock_jwt_decode, mock_current_user
):
    response = client.post(
        "/posts",
        json={"image_url": "http://example.com/image.jpg"},
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 400
    assert response.json["message"] == "Image URL and caption are required"

    response = client.post(
        "/posts",
        json={"caption": "My caption"},
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 400
    assert response.json["message"] == "Image URL and caption are required"


@patch("app.session.add")
@patch("app.session.commit")
def test_create_post_success(
    mock_commit, mock_add, client, mock_jwt_decode, mock_current_user
):
    response = client.post(
        "/posts",
        json={
            "image_url": "http://example.com/image.jpg",
            "caption": "My new post",
        },
        headers={"x-access-token": "valid_token"},
    )
    assert response.status_code == 201
    assert response.json["message"] == "Post created successfully"
    mock_add.assert_called_once()
    mock_commit.assert_called_once()
