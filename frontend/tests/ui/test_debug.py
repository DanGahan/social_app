"""
Debug UI test to understand what's happening with authentication
"""

import os

import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright

# Fix Django async issue
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


class DebugUITest(StaticLiveServerTestCase):
    """Debug what's happening with UI tests."""

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
        self.page.set_default_timeout(5000)

    def tearDown(self):
        self.context.close()
        super().tearDown()

    @pytest.mark.ui
    def test_debug_what_page_loads(self):
        """Debug what actually loads when we hit the root URL."""
        self.page.goto(f"{self.live_server_url}/")

        # Print the current URL
        current_url = self.page.url
        print(f"Current URL: {current_url}")

        # Print the page title
        title = self.page.title()
        print(f"Page title: {title}")

        # Print part of the page content to see what we got
        content = self.page.content()
        print(f"Page content preview (first 500 chars):\n{content[:500]}")

        # Check if we're on login page
        if "login" in title.lower() or "login" in content.lower():
            print("*** We're on the LOGIN page - authentication required ***")

            # Check for login form elements
            login_form = self.page.locator("form")
            if login_form.count() > 0:
                print("Login form found")

                # Look for email/username field
                email_fields = self.page.locator(
                    'input[type="email"], input[name="email"], input[name="username"]'
                )
                password_fields = self.page.locator(
                    'input[type="password"], input[name="password"]'
                )

                print(f"Email fields found: {email_fields.count()}")
                print(f"Password fields found: {password_fields.count()}")

        elif "home" in title.lower() or "posts" in content.lower():
            print("*** We're on the HOME page - success! ***")

            # Look for the elements we expect
            create_post_button = self.page.locator(".create-post-button-tab")
            posts_tab = self.page.locator('button:has-text("Posts")')

            print(f"Create post button found: {create_post_button.count()}")
            print(f"Posts tab found: {posts_tab.count()}")

        else:
            print("*** Unknown page - neither login nor home ***")

        # This test always passes - we're just debugging
        assert True
