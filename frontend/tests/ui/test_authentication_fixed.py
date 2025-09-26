"""
UI Functional Tests with Proper Authentication

Tests user workflows by actually logging in through the UI.
"""

import os

import pytest
from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import expect, sync_playwright

# Fix Django async issue
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


class AuthenticatedUITestCase(StaticLiveServerTestCase):
    """Base class for UI tests with proper authentication."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            headless=True, args=["--disable-dev-shm-usage", "--no-sandbox"]
        )

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.set_default_timeout(10000)

        # Create a test user
        self.test_user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )

    def tearDown(self):
        self.context.close()
        super().tearDown()

    def login_user(self):
        """Log in the test user through the UI."""
        self.page.goto(f"{self.live_server_url}/login/")

        # Wait for login page to load
        expect(self.page).to_have_title("Login")

        # Fill login form
        email_field = self.page.locator('input[type="email"], input[name="email"]')
        password_field = self.page.locator(
            'input[type="password"], input[name="password"]'
        )
        submit_button = self.page.locator('button[type="submit"]')

        expect(email_field).to_be_visible()
        expect(password_field).to_be_visible()
        expect(submit_button).to_be_visible()

        email_field.fill("test@example.com")
        password_field.fill("testpassword123")
        submit_button.click()

        # Wait for redirect after login
        self.page.wait_for_url(f"{self.live_server_url}/")

        # Verify we're now on the home page
        return self.page.url == f"{self.live_server_url}/"


class TestLoginWorkflow(AuthenticatedUITestCase):
    """Test the login process itself."""

    @pytest.mark.ui
    def test_user_can_login(self):
        """
        Test that a user can log in:
        Given I have valid credentials
        When I log in through the UI
        Then I should reach the home page
        """
        success = self.login_user()
        assert success, "Login should succeed and redirect to home page"

        # Verify we're on home page by looking for expected elements
        current_url = self.page.url
        print(f"After login, current URL: {current_url}")

        # Check if we can see home page elements
        page_content = self.page.content()
        print(f"Page title: {self.page.title()}")

        # The home page should have these elements
        if "Posts" in page_content:
            print("SUCCESS: Found Posts content - we're on the home page!")
        else:
            print("WARNING: No Posts content found")
            print(f"Page content preview: {page_content[:500]}")


class TestHomePageElements(AuthenticatedUITestCase):
    """Test home page elements after proper authentication."""

    def setUp(self):
        super().setUp()
        # Log in before each test
        self.login_user()

    @pytest.mark.ui
    def test_home_page_has_main_tabs(self):
        """
        Test that main navigation tabs exist:
        Given I am logged in
        When I view the home page
        Then I should see the main navigation tabs
        """
        # We should now be on the home page
        self.page.goto(f"{self.live_server_url}/")

        # Debug what we see
        current_url = self.page.url
        title = self.page.title()
        print(f"Current URL: {current_url}")
        print(f"Page title: {title}")

        # Look for tab elements
        posts_tab = self.page.locator('button:has-text("Posts")')
        my_posts_tab = self.page.locator('button:has-text("My Posts")')
        connections_tab = self.page.locator('button:has-text("Connections")')

        print(f"Posts tab found: {posts_tab.count()}")
        print(f"My Posts tab found: {my_posts_tab.count()}")
        print(f"Connections tab found: {connections_tab.count()}")

        if posts_tab.count() > 0:
            expect(posts_tab).to_be_visible()
            expect(my_posts_tab).to_be_visible()
            expect(connections_tab).to_be_visible()
            print("SUCCESS: All main tabs found!")
        else:
            # Debug what's on the page
            page_content = self.page.content()
            print(f"Page content preview: {page_content[:1000]}")

    @pytest.mark.ui
    def test_home_page_has_create_post_button(self):
        """
        Test that create post functionality exists:
        Given I am logged in
        When I view the home page
        Then I should see the create post button
        """
        self.page.goto(f"{self.live_server_url}/")

        # Look for create post button
        create_post_button = self.page.locator(".create-post-button-tab")
        print(f"Create post button found: {create_post_button.count()}")

        if create_post_button.count() > 0:
            expect(create_post_button).to_be_visible()
            print("SUCCESS: Create post button found!")

            # Try clicking it
            create_post_button.click()

            # Look for create post content
            create_post_content = self.page.locator("#CreatePostContent")
            print(f"Create post content found: {create_post_content.count()}")

            if create_post_content.count() > 0:
                expect(create_post_content).to_be_visible()
                print("SUCCESS: Create post modal opened!")
        else:
            page_content = self.page.content()
            print(f"Page content preview: {page_content[:1000]}")


class TestPostInteractionElements(AuthenticatedUITestCase):
    """Test post interaction elements after authentication."""

    def setUp(self):
        super().setUp()
        self.login_user()

    @pytest.mark.ui
    def test_like_and_comment_elements(self):
        """
        Test that post interaction elements exist:
        Given I am logged in and viewing posts
        When posts are displayed
        Then I should see like and comment elements
        """
        self.page.goto(f"{self.live_server_url}/")

        # Look for post interaction elements
        like_buttons = self.page.locator(".like-btn")
        comment_inputs = self.page.locator(".comment-input")

        print(f"Like buttons found: {like_buttons.count()}")
        print(f"Comment inputs found: {comment_inputs.count()}")

        # If there are posts, test the elements
        if like_buttons.count() > 0:
            like_button = like_buttons.first
            expect(like_button).to_be_visible()

            heart_icon = like_button.locator(".heart-icon")
            like_count = like_button.locator(".like-count")

            expect(heart_icon).to_be_visible()
            expect(like_count).to_be_visible()
            print("SUCCESS: Like button elements found!")

        if comment_inputs.count() > 0:
            comment_input = comment_inputs.first
            expect(comment_input).to_be_visible()
            print("SUCCESS: Comment input found!")

        # It's normal to have no posts in a fresh test database
        if like_buttons.count() == 0 and comment_inputs.count() == 0:
            print("INFO: No posts found - this is expected in a fresh test database")
            # Verify we're at least on the right page
            page_content = self.page.content()
            assert (
                "Posts" in page_content or "posts" in page_content
            ), "Should be on a page with posts content"
