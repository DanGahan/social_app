from unittest.mock import patch

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
