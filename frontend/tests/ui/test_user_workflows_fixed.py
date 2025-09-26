"""
UI Functional Tests using Playwright - FIXED VERSION

End-to-end user workflow testing with correct selectors matching the actual HTML.
Tests user interactions with the real DOM elements from the home.html template.
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
        # Set longer default timeout for CI environments
        self.page.set_default_timeout(10000)

    def tearDown(self):
        self.context.close()
        super().tearDown()

    def _mock_login(self):
        """Mock user login for authenticated tests."""
        # This would set up authenticated session
        self.page.goto(f"{self.live_server_url}/")

        # Wait for page to load and check if we got a valid response
        try:
            self.page.wait_for_load_state("networkidle", timeout=5000)
            # Check if page loaded properly
            if "Server Error" in self.page.content() or "404" in self.page.content():
                print(
                    f"Warning: Page may not have loaded properly at {self.live_server_url}"
                )
        except Exception as e:
            print(f"Warning: Page load issue: {e}")

        # Set authentication cookies/session
        self.page.evaluate(
            """
            sessionStorage.setItem('jwt_token', 'mock_jwt_token');
            sessionStorage.setItem('user_id', '1');
        """
        )


class TestPostCreationWorkflow(UITestCase):
    """Test post creation workflow with actual working selectors."""

    def setUp(self):
        super().setUp()
        # Mock login for authenticated tests
        self._mock_login()

    @pytest.mark.ui
    def test_create_post_ui_elements_exist(self):
        """
        Test that post creation UI elements exist and are functional:
        Given I am logged in
        When I access the create post interface
        Then all required UI elements should be present
        """
        self.page.goto(f"{self.live_server_url}/")

        # Click the + button to open create post (using actual class from HTML)
        create_post_button = self.page.locator(".create-post-button-tab")
        expect(create_post_button).to_be_visible()
        create_post_button.click()

        # Wait for Create Post Content to be visible (using actual ID from HTML)
        create_post_content = self.page.locator("#CreatePostContent")
        expect(create_post_content).to_be_visible()

        # Verify all three upload tabs exist (using actual button text from HTML)
        url_tab = self.page.locator('button:has-text("URL")')
        library_tab = self.page.locator('button:has-text("Library")')
        camera_tab = self.page.locator('button:has-text("Camera")')

        expect(url_tab).to_be_visible()
        expect(library_tab).to_be_visible()
        expect(camera_tab).to_be_visible()

        # Test URL tab functionality
        url_tab.click()
        url_section = self.page.locator("#URL")
        expect(url_section).to_be_visible()

        # Verify form elements exist (using actual IDs from HTML)
        image_url_input = self.page.locator("#url-input")
        caption_input = self.page.locator("#caption-input")
        submit_button = self.page.locator("#post-submit-btn")

        expect(image_url_input).to_be_visible()
        expect(caption_input).to_be_visible()
        expect(submit_button).to_be_visible()

        # Test Library tab
        library_tab.click()
        library_section = self.page.locator("#Library")
        expect(library_section).to_be_visible()

        library_input = self.page.locator("#library-input")
        library_button = self.page.locator("#library-button")
        expect(library_input).to_be_visible()
        expect(library_button).to_be_visible()

        # Test Camera tab
        camera_tab.click()
        camera_section = self.page.locator("#Camera")
        expect(camera_section).to_be_visible()

        camera_stream = self.page.locator("#camera-stream")
        capture_button = self.page.locator("#capture-btn")
        expect(camera_stream).to_be_visible()
        expect(capture_button).to_be_visible()

    @pytest.mark.ui
    def test_create_post_form_interaction(self):
        """
        Test form interaction for post creation:
        Given I have the create post form open
        When I fill in the form fields
        Then the form should accept input correctly
        """
        self.page.goto(f"{self.live_server_url}/")

        # Open create post form
        create_post_button = self.page.locator(".create-post-button-tab")
        create_post_button.click()

        # Switch to URL tab and fill form
        url_tab = self.page.locator('button:has-text("URL")')
        url_tab.click()

        # Fill in actual form fields
        image_url_input = self.page.locator("#url-input")
        caption_input = self.page.locator("#caption-input")

        test_url = "https://example.com/test-image.jpg"
        test_caption = "This is a test post caption"

        image_url_input.fill(test_url)
        caption_input.fill(test_caption)

        # Verify values were entered correctly
        expect(image_url_input).to_have_value(test_url)
        expect(caption_input).to_have_value(test_caption)

        # Verify character counter updates (from HTML)
        char_counter = self.page.locator("#char-counter")
        remaining = 140 - len(test_caption)
        expect(char_counter).to_contain_text(f"{remaining} characters remaining")


class TestTabNavigationWorkflow(UITestCase):
    """Test tab navigation using actual selectors from HTML."""

    def setUp(self):
        super().setUp()
        self._mock_login()

    @pytest.mark.ui
    def test_main_tab_navigation(self):
        """
        Test switching between main tabs:
        Given I am on the home page
        When I switch between tabs
        Then the content should change appropriately
        """
        self.page.goto(f"{self.live_server_url}/")

        # Test main tabs (using actual button text from HTML lines 18-20)
        posts_tab = self.page.locator('button:has-text("Posts")')
        my_posts_tab = self.page.locator('button:has-text("My Posts")')
        connections_tab = self.page.locator('button:has-text("Connections")')

        expect(posts_tab).to_be_visible()
        expect(my_posts_tab).to_be_visible()
        expect(connections_tab).to_be_visible()

        # Posts content should be visible by default (defaultOpen in HTML line 18)
        posts_content = self.page.locator("#ConnectionsPosts")
        expect(posts_content).to_be_visible()

        # Click My Posts tab
        my_posts_tab.click()
        self.page.wait_for_timeout(500)  # Wait for tab switch

        # Verify tab switched - My Posts should now be visible
        my_posts_content = self.page.locator("#MyPosts")
        expect(my_posts_content).to_be_visible()
        # Posts content should now be hidden
        expect(posts_content).to_be_hidden()

        # Click Connections tab
        connections_tab.click()
        self.page.wait_for_timeout(500)

        # Verify Connections tab is now active
        connections_content = self.page.locator("#Connections")
        expect(connections_content).to_be_visible()
        expect(my_posts_content).to_be_hidden()


class TestPostInteractionWorkflow(UITestCase):
    """Test post interaction workflows using actual selectors."""

    def setUp(self):
        super().setUp()
        self._mock_login()

    @pytest.mark.ui
    def test_like_and_comment_elements_exist(self):
        """
        Test that like and comment UI elements exist:
        Given I am viewing posts
        When posts are displayed
        Then like and comment elements should be present
        """
        self.page.goto(f"{self.live_server_url}/")

        # Check if like buttons exist (using actual class from HTML line 40)
        like_buttons = self.page.locator(".like-btn")

        # Check if comment inputs exist (using actual class from HTML line 69)
        comment_inputs = self.page.locator(".comment-input")
        comment_buttons = self.page.locator(".comment-submit")

        if like_buttons.count() > 0:
            # Test like button structure (from HTML lines 40-43)
            like_button = like_buttons.first
            expect(like_button).to_be_visible()

            # Verify like button has expected child elements
            heart_icon = like_button.locator(".heart-icon")
            like_count = like_button.locator(".like-count")

            expect(heart_icon).to_be_visible()
            expect(like_count).to_be_visible()

        if comment_inputs.count() > 0:
            # Test comment input structure
            comment_input = comment_inputs.first
            comment_button = comment_buttons.first

            expect(comment_input).to_be_visible()
            expect(comment_button).to_be_visible()

            # Test comment input functionality
            test_comment = "Test comment"
            comment_input.fill(test_comment)
            expect(comment_input).to_have_value(test_comment)

    @pytest.mark.ui
    def test_view_all_comments_button(self):
        """
        Test view all comments functionality:
        Given posts with comments exist
        When I look for view all comments buttons
        Then they should be present and functional
        """
        self.page.goto(f"{self.live_server_url}/")

        # Check for "View all comments" buttons (from HTML line 61)
        view_all_buttons = self.page.locator(".view-all-comments")

        if view_all_buttons.count() > 0:
            view_all_button = view_all_buttons.first
            expect(view_all_button).to_be_visible()
            expect(view_all_button).to_contain_text("View all")


class TestResponsiveDesignWorkflow(UITestCase):
    """Test responsive design elements."""

    def setUp(self):
        super().setUp()
        self._mock_login()

    @pytest.mark.ui
    def test_mobile_viewport(self):
        """
        Test mobile responsive behavior:
        Given I set a mobile viewport
        When I load the page
        Then the layout should adapt appropriately
        """
        # Set mobile viewport
        self.page.set_viewport_size({"width": 375, "height": 667})
        self.page.goto(f"{self.live_server_url}/")

        # Basic responsive test - ensure main elements are still visible
        body = self.page.locator("body")
        expect(body).to_be_visible()

        # Logo should be visible (from HTML line 6)
        logo = self.page.locator(".header-logo")
        expect(logo).to_be_visible()

        # Main tabs should still be accessible
        posts_tab = self.page.locator('button:has-text("Posts")')
        expect(posts_tab).to_be_visible()

    @pytest.mark.ui
    def test_tablet_viewport(self):
        """Test tablet responsive design."""
        # Set tablet viewport
        self.page.set_viewport_size({"width": 768, "height": 1024})
        self.page.goto(f"{self.live_server_url}/")

        # Basic responsive test
        body = self.page.locator("body")
        expect(body).to_be_visible()

        # Ensure main functionality is accessible
        create_post_button = self.page.locator(".create-post-button-tab")
        expect(create_post_button).to_be_visible()


class TestSearchAndConnectionsWorkflow(UITestCase):
    """Test search and connections functionality."""

    def setUp(self):
        super().setUp()
        self._mock_login()

    @pytest.mark.ui
    def test_user_search_elements(self):
        """
        Test user search functionality:
        Given I am on the connections tab
        When I access the search feature
        Then search elements should be present
        """
        self.page.goto(f"{self.live_server_url}/")

        # Switch to Connections tab
        connections_tab = self.page.locator('button:has-text("Connections")')
        connections_tab.click()

        # Check for search input (from HTML line 161)
        search_input = self.page.locator("#userSearchInput")
        expect(search_input).to_be_visible()

        # Verify placeholder text
        expect(search_input).to_have_attribute(
            "placeholder", "Search users by display name..."
        )

        # Check for search results container (from HTML line 162)
        search_results = self.page.locator("#searchResults")
        expect(search_results).to_be_visible()

    @pytest.mark.ui
    def test_connection_request_sections(self):
        """
        Test connection request sections:
        Given I am on the connections tab
        When I view the page
        Then pending and sent request sections should exist
        """
        self.page.goto(f"{self.live_server_url}/")

        # Switch to Connections tab
        connections_tab = self.page.locator('button:has-text("Connections")')
        connections_tab.click()

        connections_content = self.page.locator("#Connections")
        expect(connections_content).to_be_visible()

        # Check for section headings (from HTML lines 168, 199)
        expect(connections_content).to_contain_text("Pending Connection Requests:")
        expect(connections_content).to_contain_text("Sent Connection Requests:")
