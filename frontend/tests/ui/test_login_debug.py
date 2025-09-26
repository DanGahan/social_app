"""
Debug login process step by step
"""

import pytest
from django.contrib.auth.models import User


@pytest.fixture
def test_user(db):
    """Create a test user for debugging login."""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpassword123"
    )


@pytest.mark.ui
def test_debug_login_step_by_step(page, live_server, test_user):
    """Debug each step of the login process."""
    page.set_default_timeout(5000)

    print("\n=== STEP 1: Go to login page ===")
    page.goto(f"{live_server.url}/login/")
    print(f"URL: {page.url}")
    print(f"Title: {page.title()}")

    print("\n=== STEP 2: Find form fields ===")
    email_field = page.locator('input[type="email"], input[name="email"]')
    password_field = page.locator('input[type="password"], input[name="password"]')
    submit_button = page.locator('button[type="submit"]')

    print(f"Email field found: {email_field.count()}")
    print(f"Password field found: {password_field.count()}")
    print(f"Submit button found: {submit_button.count()}")

    print("\n=== STEP 3: Fill form ===")
    email_field.fill("test@example.com")
    password_field.fill("testpassword123")

    print(f"Email field value: {email_field.input_value()}")
    print(f"Password field filled: {len(password_field.input_value()) > 0}")

    print("\n=== STEP 4: Submit form and see what happens ===")
    print(f"Before submit - URL: {page.url}")

    # Click submit and wait a bit to see what happens
    submit_button.click()
    page.wait_for_timeout(2000)  # Wait 2 seconds

    print(f"After submit - URL: {page.url}")
    print(f"After submit - Title: {page.title()}")

    # Check if there are any error messages
    page_content = page.content()
    if "error" in page_content.lower() or "invalid" in page_content.lower():
        print("*** ERROR MESSAGES FOUND ***")
        # Look for error message elements
        error_messages = page.locator(".errorlist, .error, .alert-danger, .messages")
        if error_messages.count() > 0:
            print(f"Error message: {error_messages.first.text_content()}")

    if "success" in page_content.lower() or "welcome" in page_content.lower():
        print("*** SUCCESS MESSAGE FOUND ***")

    # Check what page we're on
    current_url = page.url
    if "/login/" in current_url:
        print("*** STILL ON LOGIN PAGE - login failed ***")
    elif current_url.endswith("/"):
        print("*** ON HOME PAGE - login succeeded! ***")
    else:
        print(f"*** ON DIFFERENT PAGE: {current_url} ***")

    print(f"\nPage content preview:\n{page_content[:800]}")

    # Always pass - this is just for debugging
    assert True
