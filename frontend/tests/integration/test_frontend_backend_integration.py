"""
Frontend-Backend Integration Tests

Tests the complete HTTP request/response flow between Django frontend
and Flask backend, including authentication, data serialization, and error handling.
"""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
from core.views import api_comments, api_create_post, api_toggle_like, api_upload_image
from django.contrib.sessions.backends.base import SessionBase
from django.test import TestCase, override_settings


class FrontendBackendIntegrationTest(TestCase):
    """Test Django frontend proxy endpoints with real backend interaction."""

    def setUp(self):
        """Set up test client and mock session data."""
        self.client = self.client_class()
        # Mock authenticated session
        session = self.client.session
        session["jwt_token"] = "mock_jwt_token"
        session["user_id"] = 1
        session.save()

    @patch("httpx.post")
    def test_api_upload_image_integration(self, mock_post):
        """Test image upload proxy with backend integration."""
        # Mock backend response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "File uploaded successfully",
            "filename": "test_image.jpg",
        }
        mock_post.return_value = mock_response

        # Create test file
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile

        test_file = SimpleUploadedFile(
            "test_image.jpg", b"fake image content", content_type="image/jpeg"
        )

        response = self.client.post("/api/posts/upload-image", {"file": test_file})

        # Verify proxy behavior
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "File uploaded successfully"
        assert data["filename"] == "test_image.jpg"

        # Verify backend was called correctly
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert "headers" in call_kwargs
        assert call_kwargs["headers"]["x-access-token"] == "mock_jwt_token"

    @patch("httpx.post")
    def test_api_create_post_integration(self, mock_post):
        """Test post creation proxy with backend integration."""
        # Mock backend response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "message": "Post created successfully",
            "post_id": 123,
        }
        mock_post.return_value = mock_response

        response = self.client.post(
            "/api/posts",
            {"image_url": "/uploads/test_image.jpg", "caption": "Test post caption"},
            content_type="application/json",
        )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Post created successfully"
        assert data["post_id"] == 123

        # Verify backend call
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["image_url"] == "/uploads/test_image.jpg"
        assert call_kwargs["json"]["caption"] == "Test post caption"

    @patch("httpx.post")
    def test_api_toggle_like_integration(self, mock_post):
        """Test like toggle proxy with backend integration."""
        # Mock backend response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "Post liked successfully",
            "action": "liked",
            "like_count": 5,
            "user_has_liked": True,
        }
        mock_post.return_value = mock_response

        response = self.client.post("/api/posts/123/like")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "liked"
        assert data["like_count"] == 5
        assert data["user_has_liked"] is True

        # Verify backend was called with correct URL
        mock_post.assert_called_once()
        args = mock_post.call_args[0]
        assert "posts/123/like" in args[0]

    @patch("httpx.post")
    @patch("httpx.get")
    def test_api_comments_post_integration(self, mock_get, mock_post):
        """Test comment creation proxy with backend integration."""
        # Mock backend response for POST
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {
            "message": "Comment added successfully",
            "comment": {
                "id": 456,
                "content": "Great post!",
                "author_display_name": "Test User",
                "created_at": "2024-01-01T12:00:00",
            },
        }
        mock_post.return_value = mock_post_response

        response = self.client.post(
            "/api/posts/123/comments",
            {"content": "Great post!"},
            content_type="application/json",
        )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["comment"]["content"] == "Great post!"
        assert data["comment"]["id"] == 456

    @patch("httpx.get")
    def test_api_comments_get_integration(self, mock_get):
        """Test comment retrieval proxy with backend integration."""
        # Mock backend response for GET
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "comments": [
                {
                    "id": 1,
                    "content": "First comment",
                    "author_display_name": "User1",
                    "created_at": "2024-01-01T10:00:00",
                },
                {
                    "id": 2,
                    "content": "Second comment",
                    "author_display_name": "User2",
                    "created_at": "2024-01-01T11:00:00",
                },
            ],
            "pagination": {"page": 1, "per_page": 10, "total": 2, "pages": 1},
        }
        mock_get.return_value = mock_response

        response = self.client.get("/api/posts/123/comments?page=1&per_page=10")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data["comments"]) == 2
        assert data["comments"][0]["content"] == "First comment"
        assert data["pagination"]["total"] == 2

    def test_unauthenticated_request_handling(self):
        """Test handling of unauthenticated requests."""
        # Clear session
        session = self.client.session
        if "jwt_token" in session:
            del session["jwt_token"]
        session.save()

        response = self.client.post("/api/posts/123/like")

        # Should redirect to login or return 401
        assert response.status_code in [302, 401]

    @patch("httpx.post")
    def test_backend_error_handling(self, mock_post):
        """Test handling of backend errors in proxy."""
        # Mock backend error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_post.return_value = mock_response

        response = self.client.post(
            "/api/posts",
            {"image_url": "/uploads/test.jpg", "caption": "Test"},
            content_type="application/json",
        )

        # Verify error is propagated
        assert response.status_code == 500

    @patch("httpx.post")
    def test_backend_timeout_handling(self, mock_post):
        """Test handling of backend timeouts."""
        # Mock timeout
        mock_post.side_effect = httpx.TimeoutException("Request timed out")

        response = self.client.post(
            "/api/posts",
            {"image_url": "/uploads/test.jpg", "caption": "Test"},
            content_type="application/json",
        )

        # Should handle timeout gracefully
        assert response.status_code == 504  # Gateway timeout

    @patch("httpx.post")
    def test_malformed_backend_response_handling(self, mock_post):
        """Test handling of malformed backend responses."""
        # Mock malformed response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response

        response = self.client.post(
            "/api/posts",
            {"image_url": "/uploads/test.jpg", "caption": "Test"},
            content_type="application/json",
        )

        # Should handle malformed response gracefully
        assert response.status_code == 502  # Bad gateway


class AuthenticationIntegrationTest(TestCase):
    """Test authentication flow integration between frontend and backend."""

    @patch("httpx.post")
    def test_login_flow_integration(self, mock_post):
        """Test complete login flow from frontend to backend."""
        # Mock successful backend login response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token": "jwt_token_12345",
            "user_id": 42,
            "message": "Login successful",
        }
        mock_post.return_value = mock_response

        response = self.client.post(
            "/login/", {"email": "test@example.com", "password": "testpassword"}
        )

        # Verify successful login redirects to home
        assert response.status_code == 302
        assert response.url == "/"

        # Verify session contains token
        session = self.client.session
        assert "jwt_token" in session
        assert session["jwt_token"] == "jwt_token_12345"

    @patch("httpx.post")
    def test_registration_flow_integration(self, mock_post):
        """Test complete registration flow from frontend to backend."""
        # Mock successful backend registration response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "user_id": 99,
            "message": "User registered successfully",
        }
        mock_post.return_value = mock_response

        response = self.client.post(
            "/register/",
            {
                "email": "newuser@example.com",
                "password": "newpassword",
                "display_name": "New User",
            },
        )

        # Verify successful registration redirects to login
        assert response.status_code == 302
        assert "login" in response.url

    def test_session_token_persistence(self):
        """Test JWT token persistence across requests."""
        # Set token in session
        session = self.client.session
        session["jwt_token"] = "persistent_token_123"
        session.save()

        # Make multiple requests
        with patch("httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_post.return_value = mock_response

            # First request
            self.client.post("/api/posts/1/like")
            # Second request
            self.client.post("/api/posts/2/like")

            # Verify same token used in both calls
            assert mock_post.call_count == 2
            for call in mock_post.call_args_list:
                headers = call[1]["headers"]
                assert headers["x-access-token"] == "persistent_token_123"


class DataSerializationIntegrationTest(TestCase):
    """Test data serialization/deserialization between frontend and backend."""

    def setUp(self):
        """Set up authenticated session."""
        session = self.client.session
        session["jwt_token"] = "test_token"
        session["user_id"] = 1
        session.save()

    @patch("httpx.post")
    def test_json_serialization(self, mock_post):
        """Test JSON data serialization in API calls."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        # Test with complex data including unicode
        test_data = {
            "caption": "Test with émojis 🎉 and unicode",
            "image_url": "/uploads/test.jpg",
        }

        response = self.client.post(
            "/api/posts", json.dumps(test_data), content_type="application/json"
        )

        # Verify data was serialized correctly
        assert response.status_code == 200
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["caption"] == "Test with émojis 🎉 and unicode"

    @patch("httpx.get")
    def test_response_deserialization(self, mock_get):
        """Test response deserialization from backend."""
        # Mock backend response with various data types
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "comments": [
                {
                    "id": 1,
                    "content": "Comment with émojis 🚀",
                    "created_at": "2024-01-01T12:00:00.123456Z",
                    "author": {"id": 42, "name": "Test User"},
                }
            ],
            "pagination": {"total": 1, "pages": 1, "current_page": 1},
        }
        mock_get.return_value = mock_response

        response = self.client.get("/api/posts/123/comments")

        # Verify complex data was deserialized correctly
        assert response.status_code == 200
        data = response.json()
        assert data["comments"][0]["content"] == "Comment with émojis 🚀"
        assert data["comments"][0]["author"]["name"] == "Test User"
        assert data["pagination"]["total"] == 1
