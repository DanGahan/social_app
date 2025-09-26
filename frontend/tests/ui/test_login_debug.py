"""
Debug login process step by step
"""

import os

import pytest
from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import expect, sync_playwright

# Fix Django async issue
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


class LoginDebugTest(StaticLiveServerTestCase):
    """Debug the login process step by step."""

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

        # Create a test user
        self.test_user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )

    def tearDown(self):
        self.context.close()
        super().tearDown()

    @pytest.mark.ui
    def test_debug_login_step_by_step(self):
        """Debug each step of the login process."""
        print("\n=== STEP 1: Go to login page ===")
        self.page.goto(f"{self.live_server_url}/login/")
        print(f"URL: {self.page.url}")
        print(f"Title: {self.page.title()}")

        print("\n=== STEP 2: Find form fields ===")
        email_field = self.page.locator('input[type="email"], input[name="email"]')
        password_field = self.page.locator(
            'input[type="password"], input[name="password"]'
        )
        submit_button = self.page.locator('button[type="submit"]')

        print(f"Email field found: {email_field.count()}")
        print(f"Password field found: {password_field.count()}")
        print(f"Submit button found: {submit_button.count()}")

        print("\n=== STEP 3: Fill form ===")
        email_field.fill("test@example.com")
        password_field.fill("testpassword123")

        print(f"Email field value: {email_field.input_value()}")
        print(f"Password field filled: {len(password_field.input_value()) > 0}")

        print("\n=== STEP 4: Submit form and see what happens ===")
        print(f"Before submit - URL: {self.page.url}")

        # Click submit and wait a bit to see what happens
        submit_button.click()
        self.page.wait_for_timeout(2000)  # Wait 2 seconds

        print(f"After submit - URL: {self.page.url}")
        print(f"After submit - Title: {self.page.title()}")

        # Check if there are any error messages
        page_content = self.page.content()
        if "error" in page_content.lower() or "invalid" in page_content.lower():
            print("*** ERROR MESSAGES FOUND ***")
            # Look for error message elements
            error_messages = self.page.locator(
                ".errorlist, .error, .alert-danger, .messages"
            )
            if error_messages.count() > 0:
                print(f"Error message: {error_messages.first.text_content()}")

        if "success" in page_content.lower() or "welcome" in page_content.lower():
            print("*** SUCCESS MESSAGE FOUND ***")

        # Check what page we're on
        current_url = self.page.url
        if "/login/" in current_url:
            print("*** STILL ON LOGIN PAGE - login failed ***")
        elif current_url.endswith("/"):
            print("*** ON HOME PAGE - login succeeded! ***")
        else:
            print(f"*** ON DIFFERENT PAGE: {current_url} ***")

        print(f"\nPage content preview:\n{page_content[:800]}")

        # Always pass - this is just for debugging
        assert True
