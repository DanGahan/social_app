from unittest.mock import MagicMock, patch

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
        # Add post functionality is now in the home view, not a separate page
        self.home_url = reverse("home")
        self.jwt_token = "fake_jwt_token"
        self.user_id = 1  # Add user_id to session

    def _set_session(self):
        session = self.client.session
        session["jwt_token"] = self.jwt_token
        session["user_id"] = self.user_id
        session.save()

    @patch("core.views.requests.get")
    def test_add_post_view_renders(self, mock_get):
        """Test that home view contains add post functionality"""
        self._set_session()

        # Mock all the requests.get calls that home view makes
        mock_responses = [
            # /users/me call
            MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "user_id": 1,
                        "profile_picture_url": "test.jpg",
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
                        "profile_picture_url": "test.jpg",
                        "bio": "Test bio",
                    }
                ),
            ),
            # Other calls
            MagicMock(status_code=200, json=MagicMock(return_value=[])),  # posts
            MagicMock(
                status_code=200, json=MagicMock(return_value=[])
            ),  # connections/posts
            MagicMock(status_code=200, json=MagicMock(return_value=[])),  # connections
            MagicMock(
                status_code=200, json=MagicMock(return_value=[])
            ),  # pending_requests
            MagicMock(
                status_code=200, json=MagicMock(return_value=[])
            ),  # sent_requests
        ]
        mock_get.side_effect = mock_responses

        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertContains(response, "Add a New Post")

    # Note: Post creation is now handled through JavaScript and API endpoints
    # These tests would require Selenium or similar for full JavaScript testing
    # For now, we focus on the API proxy endpoints which are tested in core.tests


class AddPostUIFunctionalityTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.home_url = reverse("home")  # Add post functionality is in home view
        self.jwt_token = "fake_jwt_token"
        self.user_id = 1

        # Set up authenticated session
        session = self.client.session
        session["jwt_token"] = self.jwt_token
        session["user_id"] = self.user_id
        session.save()

    @patch("core.views.requests.get")
    def test_home_page_contains_new_tabs(self, mock_get):
        """Test that home page contains the new add post tab structure"""
        # Mock all the requests.get calls that home view makes
        mock_responses = [
            MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "user_id": 1,
                        "profile_picture_url": "test.jpg",
                        "display_name": "Test User",
                    }
                ),
            ),
            MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "display_name": "Test User",
                        "profile_picture_url": "test.jpg",
                        "bio": "Test bio",
                    }
                ),
            ),
            MagicMock(status_code=200, json=MagicMock(return_value=[])),  # posts
            MagicMock(
                status_code=200, json=MagicMock(return_value=[])
            ),  # connections/posts
            MagicMock(status_code=200, json=MagicMock(return_value=[])),  # connections
            MagicMock(
                status_code=200, json=MagicMock(return_value=[])
            ),  # pending_requests
            MagicMock(
                status_code=200, json=MagicMock(return_value=[])
            ),  # sent_requests
        ]
        mock_get.side_effect = mock_responses

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")

        # Check for new tab order: Library, Camera, URL in the add post tabs
        content = response.content.decode()

        # Find the CreatePostContent section first
        createpost_start = content.find('id="CreatePostContent"')
        self.assertGreater(createpost_start, -1, "CreatePostContent section not found")

        # Look for tab buttons within this section only
        createpost_section = content[
            createpost_start : createpost_start + 5000
        ]  # Look in next 5000 chars

        library_pos = createpost_section.find(
            "onclick=\"openCreatePostTab(event, 'Library')\""
        )
        camera_pos = createpost_section.find(
            "onclick=\"openCreatePostTab(event, 'Camera')\""
        )
        url_pos = createpost_section.find("onclick=\"openCreatePostTab(event, 'URL')\"")

        # All tabs should be found
        self.assertGreater(
            library_pos, -1, "Library tab not found in CreatePostContent"
        )
        self.assertGreater(camera_pos, -1, "Camera tab not found in CreatePostContent")
        self.assertGreater(url_pos, -1, "URL tab not found in CreatePostContent")

        # Library should come first, then Camera, then URL
        self.assertLess(library_pos, camera_pos)
        self.assertLess(camera_pos, url_pos)

    @patch("core.views.requests.get")
    def test_home_page_contains_form_elements(self, mock_get):
        """Test that home page contains required add post form elements"""
        # Mock all the requests.get calls that home view makes
        mock_responses = [
            MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "user_id": 1,
                        "profile_picture_url": "test.jpg",
                        "display_name": "Test User",
                    }
                ),
            ),
            MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "display_name": "Test User",
                        "profile_picture_url": "test.jpg",
                        "bio": "Test bio",
                    }
                ),
            ),
            MagicMock(status_code=200, json=MagicMock(return_value=[])),  # posts
            MagicMock(
                status_code=200, json=MagicMock(return_value=[])
            ),  # connections/posts
            MagicMock(status_code=200, json=MagicMock(return_value=[])),  # connections
            MagicMock(
                status_code=200, json=MagicMock(return_value=[])
            ),  # pending_requests
            MagicMock(
                status_code=200, json=MagicMock(return_value=[])
            ),  # sent_requests
        ]
        mock_get.side_effect = mock_responses

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)

        # Check for form elements
        self.assertContains(response, 'id="library-input"')
        self.assertContains(response, 'id="camera-stream"')
        self.assertContains(response, 'id="url-input"')
        self.assertContains(response, 'id="caption-input"')
        self.assertContains(response, 'id="post-submit-btn"')

    @patch("core.views.requests.get")
    def test_home_page_contains_javascript_functionality(self, mock_get):
        """Test that home page contains JavaScript for camera and upload functionality"""
        # Mock all the requests.get calls that home view makes
        mock_responses = [
            MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "user_id": 1,
                        "profile_picture_url": "test.jpg",
                        "display_name": "Test User",
                    }
                ),
            ),
            MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "display_name": "Test User",
                        "profile_picture_url": "test.jpg",
                        "bio": "Test bio",
                    }
                ),
            ),
            MagicMock(status_code=200, json=MagicMock(return_value=[])),  # posts
            MagicMock(
                status_code=200, json=MagicMock(return_value=[])
            ),  # connections/posts
            MagicMock(status_code=200, json=MagicMock(return_value=[])),  # connections
            MagicMock(
                status_code=200, json=MagicMock(return_value=[])
            ),  # pending_requests
            MagicMock(
                status_code=200, json=MagicMock(return_value=[])
            ),  # sent_requests
        ]
        mock_get.side_effect = mock_responses

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Check for key JavaScript functions
        self.assertIn("openCreatePostTab", content)
        self.assertIn("startCamera", content)
        self.assertIn("captureBtn.addEventListener", content)
        self.assertIn("library-input", content)

    # Note: Post creation workflow is now handled via JavaScript and API proxy endpoints
    # Full integration testing would require Selenium or similar browser automation
    # The API proxy endpoints are tested in core.tests.ApiProxyTests
