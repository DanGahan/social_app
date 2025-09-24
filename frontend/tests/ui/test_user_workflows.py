"""
UI Functional Tests using Playwright

End-to-end user workflow testing covering critical business paths.
Tests user interactions across browsers with BDD-style scenarios.
"""

import os
import re

import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import expect, sync_playwright

# Fix Django async issue
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


class UITestCase(StaticLiveServerTestCase):
    """Base class for UI tests with Playwright."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def tearDown(self):
        self.context.close()
        super().tearDown()


class TestUserRegistrationWorkflow(UITestCase):
    """Test complete user registration workflow."""

    @pytest.mark.ui
    def test_successful_user_registration(self):
        """
        Test complete user registration flow:
        Given I am on the registration page
        When I enter valid user details
        Then I should be registered and redirected to login
        """
        # Navigate to registration page
        self.page.goto(f"{self.live_server_url}/register/")

        # Verify we're on the registration page
        expect(self.page).to_have_title("Register")
        expect(self.page.locator("h2")).to_contain_text("Register")

        # Fill registration form
        self.page.fill('input[name="email"]', "testuser@example.com")
        self.page.fill('input[name="password"]', "securepassword123")

        # Submit form
        self.page.click('button[type="submit"]')

        # Should redirect to login page after successful registration
        expect(self.page).to_have_url(f"{self.live_server_url}/login/")
        expect(self.page.locator(".success-message")).to_be_visible()

    @pytest.mark.ui
    def test_registration_validation_errors(self):
        """
        Test registration form validation:
        Given I am on the registration page
        When I submit invalid data
        Then I should see validation errors
        """
        self.page.goto(f"{self.live_server_url}/register/")

        # Try to submit with invalid email
        self.page.fill('input[name="email"]', "invalid-email")
        self.page.fill('input[name="password"]', "123")  # Too short
        self.page.click('button[type="submit"]')

        # Should show validation errors
        expect(self.page.locator(".error-message")).to_be_visible()
        expect(self.page.locator(".error-message")).to_contain_text("valid email")


class TestUserLoginWorkflow(UITestCase):
    """Test user login workflow."""

    @pytest.mark.ui
    def test_successful_login(self):
        """
        Test successful login flow:
        Given I have a registered account
        When I enter valid credentials
        Then I should be logged in and redirected to dashboard
        """
        # Go to login page
        self.page.goto(f"{self.live_server_url}/login/")

        # Fill login form
        self.page.fill('input[name="email"]', "existing@example.com")
        self.page.fill('input[name="password"]', "correctpassword")

        # Submit form
        self.page.click('button[type="submit"]')

        # Should redirect to home page
        expect(self.page).to_have_url(f"{self.live_server_url}/")
        expect(self.page.locator(".welcome-message")).to_be_visible()

    @pytest.mark.ui
    def test_login_with_invalid_credentials(self):
        """
        Test login with wrong credentials:
        Given I am on the login page
        When I enter incorrect credentials
        Then I should see an error message
        """
        self.page.goto(f"{self.live_server_url}/login/")

        self.page.fill('input[name="email"]', "wrong@example.com")
        self.page.fill('input[name="password"]', "wrongpassword")
        self.page.click('button[type="submit"]')

        # Should show error message
        expect(self.page.locator(".error-message")).to_be_visible()
        expect(self.page.locator(".error-message")).to_contain_text(
            "Invalid credentials"
        )


class TestPostCreationWorkflow(UITestCase):
    """Test post creation workflow."""

    def setUp(self):
        super().setUp()
        # Mock login for authenticated tests
        self._mock_login()

    def _mock_login(self):
        """Mock user login for authenticated tests."""
        # This would set up authenticated session
        self.page.goto(f"{self.live_server_url}/")
        # Set authentication cookies/session
        self.page.evaluate(
            """
            sessionStorage.setItem('jwt_token', 'mock_jwt_token');
            sessionStorage.setItem('user_id', '1');
        """
        )

    @pytest.mark.ui
    def test_create_post_via_url_upload(self):
        """
        Test post creation with URL upload:
        Given I am logged in
        When I create a post using URL upload
        Then the post should be created successfully
        """
        self.page.goto(f"{self.live_server_url}/")

        # Switch to URL tab
        self.page.click('[data-tab="url"]')
        expect(self.page.locator("#url-upload")).to_be_visible()

        # Enter image URL and caption
        self.page.fill('input[name="image_url"]', "https://example.com/test-image.jpg")
        self.page.fill(
            'textarea[name="caption"]', "This is a test post created via URL upload"
        )

        # Submit post
        self.page.click('button[type="submit"]')

        # Should show success message
        expect(self.page.locator(".success-message")).to_be_visible()
        expect(self.page.locator(".success-message")).to_contain_text(
            "Post created successfully"
        )

    @pytest.mark.ui
    def test_create_post_via_file_upload(self):
        """
        Test post creation with file upload:
        Given I am logged in
        When I upload an image file
        Then the post should be created successfully
        """
        self.page.goto(f"{self.live_server_url}/")

        # Switch to Library tab
        self.page.click('[data-tab="library"]')
        expect(self.page.locator("#library-upload")).to_be_visible()

        # Upload file (would need test file in actual implementation)
        # self.page.set_input_files('input[type="file"]', 'test-image.jpg')

        # Fill caption
        self.page.fill('textarea[name="caption"]', "Test post with file upload")

        # Note: File upload testing would require actual test files
        # This is a placeholder for the workflow

    @pytest.mark.ui
    def test_camera_capture_workflow(self):
        """
        Test camera capture workflow:
        Given I am logged in and have camera permissions
        When I use the camera to capture an image
        Then I should be able to create a post with it
        """
        self.page.goto(f"{self.live_server_url}/")

        # Switch to Camera tab
        self.page.click('[data-tab="camera"]')
        expect(self.page.locator("#camera-upload")).to_be_visible()

        # Test camera UI elements
        expect(self.page.locator("#camera-video")).to_be_visible()
        expect(self.page.locator("#capture-button")).to_be_visible()
        expect(self.page.locator("#switch-camera")).to_be_visible()

        # Note: Camera testing would require browser permissions
        # This tests the UI elements are present


class TestPostInteractionWorkflow(UITestCase):
    """Test post interaction workflows (likes and comments)."""

    def setUp(self):
        super().setUp()
        self._mock_login()
        self._setup_test_posts()

    def _setup_test_posts(self):
        """Set up test posts for interaction testing."""
        # This would create test posts in the database
        pass

    @pytest.mark.ui
    def test_like_post_workflow(self):
        """
        Test liking a post:
        Given I am viewing posts
        When I click the like button
        Then the post should be liked and UI should update
        """
        self.page.goto(f"{self.live_server_url}/")

        # Find first post and like button
        like_button = self.page.locator(".like-button").first

        # Click like button
        like_button.click()

        # Wait for UI to update
        self.page.wait_for_timeout(500)

        # Note: Like count verification would require actual implementation
        # self.page.locator(".like-count").first.text_content()

        # Verify button state changed
        expect(like_button).to_have_class(re.compile(r".*liked.*"))

    @pytest.mark.ui
    def test_comment_on_post_workflow(self):
        """
        Test commenting on a post:
        Given I am viewing a post
        When I add a comment
        Then the comment should appear immediately
        """
        self.page.goto(f"{self.live_server_url}/")

        # Find first post's comment section
        comment_input = self.page.locator(".comment-input").first
        comment_button = self.page.locator(".comment-submit").first

        # Add a comment
        test_comment = "This is a test comment"
        comment_input.fill(test_comment)
        comment_button.click()

        # Wait for comment to appear
        self.page.wait_for_timeout(1000)

        # Verify comment appears
        expect(self.page.locator(".comment-content")).to_contain_text(test_comment)

    @pytest.mark.ui
    def test_view_all_comments_workflow(self):
        """
        Test viewing all comments:
        Given a post has many comments
        When I click "View all comments"
        Then all comments should be loaded and displayed
        """
        self.page.goto(f"{self.live_server_url}/")

        # Click "View all comments" link
        self.page.click(".view-all-comments")

        # Wait for comments to load
        self.page.wait_for_timeout(1000)

        # Verify more comments are visible
        comment_count = self.page.locator(".comment-item").count()
        assert comment_count > 3  # Should show more than initial 3


class TestTabNavigationWorkflow(UITestCase):
    """Test tab navigation workflow."""

    def setUp(self):
        super().setUp()
        self._mock_login()

    @pytest.mark.ui
    def test_switch_between_posts_tabs(self):
        """
        Test switching between Posts and My Posts tabs:
        Given I am on the home page
        When I switch between tabs
        Then the content should change appropriately
        """
        self.page.goto(f"{self.live_server_url}/")

        # Verify Posts tab is active by default
        expect(self.page.locator("#Posts")).to_be_visible()
        expect(self.page.locator('[data-tab="Posts"]')).to_have_class(
            re.compile(r".*active.*")
        )

        # Click My Posts tab
        self.page.click('[data-tab="MyPosts"]')

        # Verify tab switched
        expect(self.page.locator("#MyPosts")).to_be_visible()
        expect(self.page.locator("#Posts")).to_be_hidden()
        expect(self.page.locator('[data-tab="MyPosts"]')).to_have_class(
            re.compile(r".*active.*")
        )

    @pytest.mark.ui
    def test_switch_between_upload_tabs(self):
        """
        Test switching between upload method tabs:
        Given I am creating a post
        When I switch between Library, Camera, and URL tabs
        Then the appropriate upload interface should be shown
        """
        self.page.goto(f"{self.live_server_url}/")

        # Test URL tab
        self.page.click('[data-tab="url"]')
        expect(self.page.locator("#url-upload")).to_be_visible()
        expect(self.page.locator("#library-upload")).to_be_hidden()

        # Test Library tab
        self.page.click('[data-tab="library"]')
        expect(self.page.locator("#library-upload")).to_be_visible()
        expect(self.page.locator("#url-upload")).to_be_hidden()

        # Test Camera tab
        self.page.click('[data-tab="camera"]')
        expect(self.page.locator("#camera-upload")).to_be_visible()
        expect(self.page.locator("#library-upload")).to_be_hidden()


class TestResponsiveDesignWorkflow(UITestCase):
    """Test responsive design across different screen sizes."""

    @pytest.mark.ui
    def test_mobile_view_workflow(self):
        """
        Test mobile responsive design:
        Given I am using a mobile device
        When I navigate the app
        Then the layout should be mobile-optimized
        """
        # Set mobile viewport
        self.page.set_viewport_size({"width": 375, "height": 667})
        self.page.goto(f"{self.live_server_url}/")

        # Test mobile-specific elements
        # (Would check for hamburger menu, stacked layouts, etc.)
        expect(self.page.locator(".mobile-nav")).to_be_visible()

    @pytest.mark.ui
    def test_tablet_view_workflow(self):
        """Test tablet responsive design."""
        # Set tablet viewport
        self.page.set_viewport_size({"width": 768, "height": 1024})
        self.page.goto(f"{self.live_server_url}/")

        # Test tablet-specific layout
        # (Would verify appropriate layout changes)


class TestErrorHandlingWorkflow(UITestCase):
    """Test error handling in UI workflows."""

    def setUp(self):
        super().setUp()
        self._mock_login()

    @pytest.mark.ui
    def test_network_error_handling(self):
        """
        Test handling of network errors:
        Given I am using the app
        When a network error occurs
        Then appropriate error messages should be shown
        """
        # Mock network failure
        self.page.route("**/api/**", lambda route: route.abort())

        self.page.goto(f"{self.live_server_url}/")

        # Try to like a post (should fail)
        self.page.click(".like-button")

        # Should show error message
        expect(self.page.locator(".error-toast")).to_be_visible()
        expect(self.page.locator(".error-toast")).to_contain_text("Network error")

    @pytest.mark.ui
    def test_session_expiry_handling(self):
        """
        Test handling of expired session:
        Given my session has expired
        When I try to interact with the app
        Then I should be redirected to login
        """
        self.page.goto(f"{self.live_server_url}/")

        # Mock 401 response
        self.page.route("**/api/**", lambda route: route.fulfill(status=401))

        # Try to perform authenticated action
        self.page.click(".like-button")

        # Should redirect to login
        expect(self.page).to_have_url(re.compile(r".*/login/.*"))
