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


class LikesCommentsApiProxyTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Set up authenticated session
        session = self.client.session
        session["jwt_token"] = "fake_jwt_token"
        session["user_id"] = 1
        session.save()

    @patch("core.views.requests.post")
    def test_api_toggle_like_success(self, mock_post):
        """Test successful like toggle through proxy"""
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {
            "message": "Post liked successfully",
            "action": "liked",
            "like_count": 5,
            "user_has_liked": True,
        }

        response = self.client.post(reverse("api_toggle_like", args=[1]))

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["action"], "liked")
        self.assertEqual(response_data["like_count"], 5)
        self.assertTrue(response_data["user_has_liked"])

    @patch("core.views.requests.post")
    def test_api_toggle_like_unlike_success(self, mock_post):
        """Test successful unlike through proxy"""
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {
            "message": "Post unliked successfully",
            "action": "unliked",
            "like_count": 4,
            "user_has_liked": False,
        }

        response = self.client.post(reverse("api_toggle_like", args=[1]))

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["action"], "unliked")
        self.assertEqual(response_data["like_count"], 4)
        self.assertFalse(response_data["user_has_liked"])

    def test_api_toggle_like_unauthorized(self):
        """Test like toggle without authentication"""
        # Clear session
        self.client.session.flush()

        response = self.client.post(reverse("api_toggle_like", args=[1]))

        self.assertEqual(response.status_code, 401)
        response_data = response.json()
        self.assertEqual(response_data["error"], "Unauthorized")

    @patch("core.views.requests.post")
    def test_api_toggle_like_backend_error(self, mock_post):
        """Test like toggle with backend error"""
        mock_post.return_value.ok = False
        mock_post.return_value.status_code = 403
        mock_post.return_value.json.return_value = {
            "message": "Access denied. You can only like posts from connections."
        }

        response = self.client.post(reverse("api_toggle_like", args=[1]))

        self.assertEqual(response.status_code, 403)

    @patch("core.views.requests.post")
    def test_api_add_comment_success(self, mock_post):
        """Test successful comment creation through proxy"""
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {
            "message": "Comment added successfully",
            "comment": {
                "id": 1,
                "content": "Great post!",
                "created_at": "2023-01-01T00:00:00",
                "user_id": 1,
                "author_display_name": "Test User",
                "author_profile_picture_url": "test.jpg",
            },
        }

        import json

        response = self.client.post(
            reverse("api_comments", args=[1]),
            data=json.dumps({"content": "Great post!"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["message"], "Comment added successfully")
        self.assertEqual(response_data["comment"]["content"], "Great post!")

    @patch("core.views.requests.post")
    def test_api_add_comment_empty_content(self, mock_post):
        """Test comment creation with empty content"""
        mock_post.return_value.ok = False
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {
            "message": "Comment content is required"
        }

        import json

        response = self.client.post(
            reverse("api_comments", args=[1]),
            data=json.dumps({"content": ""}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    @patch("core.views.requests.post")
    def test_api_add_comment_too_long(self, mock_post):
        """Test comment creation with content too long"""
        mock_post.return_value.ok = False
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {
            "message": "Comment must be 500 characters or less"
        }

        import json

        response = self.client.post(
            reverse("api_comments", args=[1]),
            data=json.dumps({"content": "A" * 501}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_api_add_comment_unauthorized(self):
        """Test comment creation without authentication"""
        # Clear session
        self.client.session.flush()

        import json

        response = self.client.post(
            reverse("api_comments", args=[1]),
            data=json.dumps({"content": "Great post!"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        response_data = response.json()
        self.assertEqual(response_data["error"], "Unauthorized")

    @patch("core.views.requests.get")
    def test_api_get_comments_success(self, mock_get):
        """Test successful comment retrieval through proxy"""
        mock_get.return_value.ok = True
        mock_get.return_value.json.return_value = {
            "comments": [
                {
                    "id": 1,
                    "content": "Great post!",
                    "created_at": "2023-01-01T00:00:00",
                    "user_id": 2,
                    "author_display_name": "Commenter",
                    "author_profile_picture_url": "commenter.jpg",
                }
            ],
            "pagination": {"page": 1, "per_page": 10, "total": 1, "pages": 1},
        }

        response = self.client.get(reverse("api_comments", args=[1]))

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["comments"]), 1)
        self.assertEqual(response_data["comments"][0]["content"], "Great post!")
        self.assertEqual(response_data["pagination"]["total"], 1)

    @patch("core.views.requests.get")
    def test_api_get_comments_with_pagination(self, mock_get):
        """Test comment retrieval with pagination parameters"""
        mock_get.return_value.ok = True
        mock_get.return_value.json.return_value = {
            "comments": [],
            "pagination": {"page": 2, "per_page": 5, "total": 10, "pages": 2},
        }

        response = self.client.get(
            reverse("api_comments", args=[1]) + "?page=2&per_page=5"
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["pagination"]["page"], 2)
        self.assertEqual(response_data["pagination"]["per_page"], 5)

    def test_api_get_comments_unauthorized(self):
        """Test comment retrieval without authentication"""
        # Clear session
        self.client.session.flush()

        response = self.client.get(reverse("api_comments", args=[1]))

        self.assertEqual(response.status_code, 401)
        response_data = response.json()
        self.assertEqual(response_data["error"], "Unauthorized")

    @patch("core.views.requests.get")
    def test_api_get_comments_post_not_found(self, mock_get):
        """Test comment retrieval for non-existent post"""
        mock_get.return_value.ok = False
        mock_get.return_value.status_code = 404
        mock_get.return_value.json.return_value = {"message": "Post not found"}

        response = self.client.get(reverse("api_comments", args=[999]))

        self.assertEqual(response.status_code, 404)
