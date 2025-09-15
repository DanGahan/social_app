from unittest.mock import patch

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
        self.assertEqual(str(messages_list[0]), "Registration successful! Please log in.")

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
        response = self.client.post(self.login_url, {"email": "invalid-email", "password": ""})

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
