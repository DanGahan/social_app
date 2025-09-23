from unittest.mock import MagicMock, patch

from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse


class CoreViewsTest(TestCase):
    def setUp(self):
        self.client = Client()  # Use Django test Client
        self.register_url = reverse("register")
        self.login_url = reverse("login")
        self.home_url = reverse("home")  # Add home_url

    @patch("core.views.requests.post")
    def test_register_view_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status.return_value = None

        response = self.client.post(
            self.register_url,
            {
                "email": "test@example.com",
                "password": "password123",
                "confirm_password": "password123",
            },
        )

        self.assertEqual(response.status_code, 302)  # Redirects on success
        self.assertEqual(response.url, self.login_url)
        # Check messages using Django's message storage
        messages_list = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]), "Registration successful! Please log in."
        )

    @patch("core.views.requests.post")
    def test_register_view_invalid_form(self, mock_post):
        response = self.client.post(
            self.register_url,
            {
                "email": "invalid-email",
                "password": "123",
                "confirm_password": "456",
            },
        )

        self.assertEqual(response.status_code, 200)  # Renders form again
        messages_list = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Please correct the errors below.")
        mock_post.assert_not_called()  # Backend not called for invalid form

    @patch("core.views.requests.post")
    def test_register_view_backend_error(self, mock_post):
        from requests.exceptions import RequestException

        mock_post.side_effect = RequestException("Backend error")

        response = self.client.post(
            self.register_url,
            {
                "email": "test@example.com",
                "password": "password123",
                "confirm_password": "password123",
            },
        )

        self.assertEqual(response.status_code, 200)  # Renders form again
        messages_list = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Registration failed: Backend error")

    @patch("core.views.requests.post")
    def test_login_view_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"token": "fake_jwt_token"}
        mock_post.return_value.raise_for_status.return_value = None

        response = self.client.post(
            self.login_url,
            {"email": "test@example.com", "password": "password123"},
        )

        self.assertEqual(response.status_code, 302)  # Redirects on success
        self.assertEqual(response.url, self.home_url)
        self.assertEqual(self.client.session["jwt_token"], "fake_jwt_token")

    @patch("core.views.requests.post")
    def test_login_view_invalid_form(self, mock_post):
        response = self.client.post(
            self.login_url, {"email": "invalid-email", "password": ""}
        )

        self.assertEqual(response.status_code, 200)  # Renders form again
        messages_list = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Please correct the errors below.")
        mock_post.assert_not_called()  # Backend not called for invalid form

    @patch("core.views.requests.post")
    def test_login_view_backend_error(self, mock_post):
        from requests.exceptions import RequestException

        mock_post.side_effect = RequestException("Login backend error")

        response = self.client.post(
            self.login_url,
            {"email": "test@example.com", "password": "password123"},
        )

        self.assertEqual(response.status_code, 200)  # Renders form again
        messages_list = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Login failed: Login backend error")

    @patch("core.views.requests.post")
    def test_login_view_invalid_response_from_backend(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {}  # No token in response
        mock_post.return_value.raise_for_status.return_value = None

        response = self.client.post(
            self.login_url,
            {"email": "test@example.com", "password": "password123"},
        )

        self.assertEqual(response.status_code, 200)  # Renders form again
        messages_list = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]),
            "Login failed: Invalid response from server.",
        )

    @patch("core.views.requests.get")
    def test_home_view_authenticated_user(self, mock_get):
        """Test home view with authenticated user"""
        # Set up session data
        session = self.client.session
        session["jwt_token"] = "fake_jwt_token"
        session["user_id"] = 1
        session["profile_picture_url"] = "http://example.com/pic.jpg"
        session["display_name"] = "Test User"
        session.save()

        # Mock all the requests.get calls that home view makes
        mock_responses = [
            # /users/me call
            MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "user_id": 1,
                        "profile_picture_url": "http://example.com/pic.jpg",
                        "display_name": "Test User",
                    }
                ),
            ),
            # /users/1/profile call
            MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "display_name": "Test User",
                        "profile_picture_url": "http://example.com/pic.jpg",
                        "bio": "Test bio",
                    }
                ),
            ),
            # /users/1/posts call
            MagicMock(status_code=200, json=MagicMock(return_value=[])),
            # /users/1/connections/posts call
            MagicMock(status_code=200, json=MagicMock(return_value=[])),
            # /users/1/connections call
            MagicMock(status_code=200, json=MagicMock(return_value=[])),
            # /users/1/pending_requests call
            MagicMock(status_code=200, json=MagicMock(return_value=[])),
            # /users/1/sent_requests call
            MagicMock(status_code=200, json=MagicMock(return_value=[])),
        ]
        mock_get.side_effect = mock_responses

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertContains(response, "Add a New Post")
        self.assertContains(response, "Library")  # Check for new tab order


class ApiProxyTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Set up authenticated session
        session = self.client.session
        session["jwt_token"] = "fake_jwt_token"
        session["user_id"] = 1
        session.save()

    @patch("core.views.requests.post")
    def test_api_upload_image_success(self, mock_post):
        """Test successful image upload through proxy"""
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {
            "message": "File uploaded successfully",
            "filename": "/uploads/test.png",
        }

        # Create a test file
        from django.core.files.uploadedfile import SimpleUploadedFile

        test_file = SimpleUploadedFile(
            "test.png", b"file_content", content_type="image/png"
        )

        response = self.client.post(reverse("api_upload_image"), {"file": test_file})

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["message"], "File uploaded successfully")
        self.assertEqual(response_data["filename"], "/uploads/test.png")

    def test_api_upload_image_no_file(self):
        """Test upload endpoint with no file"""
        response = self.client.post(reverse("api_upload_image"), {})

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data["error"], "No file provided")

    def test_api_upload_image_unauthorized(self):
        """Test upload endpoint without authentication"""
        # Clear session
        self.client.session.flush()

        from django.core.files.uploadedfile import SimpleUploadedFile

        test_file = SimpleUploadedFile(
            "test.png", b"file_content", content_type="image/png"
        )

        response = self.client.post(reverse("api_upload_image"), {"file": test_file})

        self.assertEqual(response.status_code, 401)
        response_data = response.json()
        self.assertEqual(response_data["error"], "Unauthorized")

    @patch("core.views.requests.post")
    def test_api_create_post_success(self, mock_post):
        """Test successful post creation through proxy"""
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {
            "message": "Post created successfully",
            "post_id": 1,
        }

        import json

        response = self.client.post(
            reverse("api_create_post"),
            data=json.dumps(
                {
                    "image_url": "http://example.com/image.jpg",
                    "caption": "Test caption",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["message"], "Post created successfully")

    def test_api_create_post_unauthorized(self):
        """Test post creation without authentication"""
        # Clear session
        self.client.session.flush()

        import json

        response = self.client.post(
            reverse("api_create_post"),
            data=json.dumps(
                {
                    "image_url": "http://example.com/image.jpg",
                    "caption": "Test caption",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        response_data = response.json()
        self.assertEqual(response_data["error"], "Unauthorized")

    @patch("core.views.requests.get")
    def test_serve_uploaded_image_success(self, mock_get):
        """Test serving uploaded images through proxy"""
        mock_get.return_value.ok = True
        mock_get.return_value.content = b"fake_image_data"
        mock_get.return_value.headers = {"content-type": "image/png"}

        response = self.client.get(reverse("serve_uploaded_image", args=["test.png"]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"fake_image_data")
        self.assertEqual(response["Content-Type"], "image/png")

    @patch("core.views.requests.get")
    def test_serve_uploaded_image_not_found(self, mock_get):
        """Test serving non-existent image"""
        mock_get.return_value.ok = False

        response = self.client.get(
            reverse("serve_uploaded_image", args=["nonexistent.png"])
        )

        self.assertEqual(response.status_code, 404)
