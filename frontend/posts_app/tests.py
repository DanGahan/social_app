from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse


class PostsAppViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_id = 123
        self.post_list_url = reverse("post_list", args=[self.user_id])

    @patch("posts_app.views.requests.get")
    def test_post_list_success(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": 1,
                "image_url": "http://example.com/img1.jpg",
                "caption": "Test Post 1",
            },
            {
                "id": 2,
                "image_url": "http://example.com/img2.jpg",
                "caption": "Test Post 2",
            },
        ]

        response = self.client.get(self.post_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "posts_app/post_list.html")
        self.assertContains(response, "Test Post 1")
        self.assertContains(response, "Test Post 2")

    @patch("posts_app.views.requests.get")
    def test_post_list_backend_error(self, mock_get):
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("Backend error")

        response = self.client.get(self.post_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "posts_app/post_list.html")
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertTrue("Error fetching posts:" in str(messages[0]))
        self.assertNotContains(response, "Test Post 1")
        self.assertNotContains(response, "Test Post 2")


class AddPostViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.add_post_url = reverse("add_post")
        self.jwt_token = "fake_jwt_token"
        self.user_id = 1  # Add user_id to session

    def _set_session(self):
        session = self.client.session
        session["jwt_token"] = self.jwt_token
        session["user_id"] = self.user_id
        session.save()

    def test_add_post_view_renders(self):
        self._set_session()
        response = self.client.get(self.add_post_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "posts_app/add_post.html")
        self.assertContains(response, "Add a New Post")

    @patch("posts_app.views.requests.post")
    def test_add_post_success_with_image_url(self, mock_requests_post):
        self._set_session()
        # Mock the backend /posts endpoint call
        mock_requests_post.return_value.status_code = 201
        mock_requests_post.return_value.json.return_value = {
            "message": "Post created successfully",
            "post_id": 1,
        }
        mock_requests_post.return_value.raise_for_status.return_value = None

        response = self.client.post(
            self.add_post_url,
            {
                "image_url": "http://example.com/image.jpg",
                "caption": "My test post",
                "image_source": "url",  # Indicate that image is from URL
            },
            HTTP_X_ACCESS_TOKEN=self.jwt_token,  # Pass token in header
        )

        self.assertEqual(response.status_code, 302)  # Should redirect on success
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Post created successfully!")
        mock_requests_post.assert_called_once_with(
            "http://social_backend:5000/posts",
            json={"image_url": "http://example.com/image.jpg", "caption": "My test post"},
            headers={"x-access-token": self.jwt_token},
        )

    @patch("posts_app.views.requests.post")
    def test_add_post_missing_caption(self, mock_requests_post):
        self._set_session()
        response = self.client.post(
            self.add_post_url,
            {"image_url": "http://example.com/image.jpg", "caption": "", "image_source": "url"},
            HTTP_X_ACCESS_TOKEN=self.jwt_token,
        )

        self.assertEqual(response.status_code, 200)  # Should re-render form
        self.assertContains(response, "Caption is required.")
        mock_requests_post.assert_not_called()

    @patch("posts_app.views.requests.post")
    def test_add_post_missing_image_url(self, mock_requests_post):
        self._set_session()
        response = self.client.post(
            self.add_post_url,
            {"image_url": "", "caption": "My test post", "image_source": "url"},
            HTTP_X_ACCESS_TOKEN=self.jwt_token,
        )

        self.assertEqual(response.status_code, 200)  # Should re-render form
        self.assertContains(response, "Image URL is required.")
        mock_requests_post.assert_not_called()

    @patch("posts_app.views.requests.post")
    def test_add_post_backend_error(self, mock_requests_post):
        self._set_session()
        from requests.exceptions import RequestException

        mock_requests_post.side_effect = RequestException("Backend post error")

        response = self.client.post(
            self.add_post_url,
            {
                "image_url": "http://example.com/image.jpg",
                "caption": "My test post",
                "image_source": "url",
            },
            HTTP_X_ACCESS_TOKEN=self.jwt_token,
        )

        self.assertEqual(response.status_code, 200)  # Should re-render form
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Error creating post: Backend post error")
        mock_requests_post.assert_called_once()
