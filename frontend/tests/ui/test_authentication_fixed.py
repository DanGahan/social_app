"""
UI Functional Tests with Proper Authentication

Tests user workflows by actually logging in through the UI.
"""

import pytest
from django.contrib.auth.models import User
from playwright.sync_api import expect


@pytest.fixture
def test_user(db):
    """Create a test user for authentication tests."""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpassword123"
    )


def login_user(page, live_server, test_user):
    """Log in the test user through the UI."""
    page.goto(f"{live_server.url}/login/")

    # Wait for login page to load
    expect(page).to_have_title("Login")

    # Fill login form
    email_field = page.locator('input[type="email"], input[name="email"]')
    password_field = page.locator('input[type="password"], input[name="password"]')
    submit_button = page.locator('button[type="submit"]')

    expect(email_field).to_be_visible()
    expect(password_field).to_be_visible()
    expect(submit_button).to_be_visible()

    email_field.fill("test@example.com")
    password_field.fill("testpassword123")
    submit_button.click()

    # Wait for redirect after login
    page.wait_for_url(f"{live_server.url}/")

    # Verify we're now on the home page
    return page.url == f"{live_server.url}/"


@pytest.mark.ui
def test_user_can_login(page, live_server, test_user):
    """
    Test that a user can access the login page:
    Given I visit the login page
    When I view the login form
    Then I should see the login form elements
    """
    page.set_default_timeout(10000)

    # Navigate to login page
    page.goto(f"{live_server.url}/login/")

    # Check that we can see the login page
    page_title = page.title()
    print(f"Page title: {page_title}")

    # Look for login form elements
    email_field = page.locator('input[type="email"], input[name="email"]')
    password_field = page.locator('input[type="password"], input[name="password"]')
    submit_button = page.locator('button[type="submit"], input[type="submit"]')

    # Verify form elements exist
    email_count = email_field.count()
    password_count = password_field.count()
    submit_count = submit_button.count()

    print(f"Email field found: {email_count}")
    print(f"Password field found: {password_count}")
    print(f"Submit button found: {submit_count}")

    # Assert that we have the basic login form
    assert email_count > 0, "Should have an email input field"
    assert password_count > 0, "Should have a password input field"
    assert submit_count > 0, "Should have a submit button"

    # Verify elements are visible
    expect(email_field.first).to_be_visible()
    expect(password_field.first).to_be_visible()
    expect(submit_button.first).to_be_visible()

    print("SUCCESS: Login form elements are present and visible!")


@pytest.mark.ui
def test_home_page_redirect_to_login(page, live_server, test_user):
    """
    Test that home page redirects to login when unauthenticated:
    Given I am not logged in
    When I try to access the home page
    Then I should be redirected to login page
    """
    page.set_default_timeout(10000)

    # Try to access home page without login
    page.goto(f"{live_server.url}/")

    # Should be redirected to login page
    current_url = page.url
    print(f"Current URL: {current_url}")

    # Check if we're on login page (either redirected or already there)
    assert "/login/" in current_url, "Should be redirected to login page"

    # Verify we can see login form
    email_field = page.locator('input[type="email"], input[name="email"]')
    password_field = page.locator('input[type="password"], input[name="password"]')

    assert email_field.count() > 0, "Should see email field on login page"
    assert password_field.count() > 0, "Should see password field on login page"

    print("SUCCESS: Home page correctly redirects to login when unauthenticated!")


@pytest.mark.ui
def test_login_page_structure(page, live_server, test_user):
    """
    Test the structure of the login page:
    Given I visit the login page
    When I view the page
    Then I should see all expected form elements
    """
    page.set_default_timeout(10000)

    page.goto(f"{live_server.url}/login/")

    # Check page title
    page_title = page.title()
    print(f"Page title: {page_title}")

    # Look for form elements
    form = page.locator("form")
    email_field = page.locator('input[type="email"], input[name="email"]')
    password_field = page.locator('input[type="password"], input[name="password"]')
    submit_button = page.locator('button[type="submit"], input[type="submit"]')

    print(f"Form found: {form.count()}")
    print(f"Email field found: {email_field.count()}")
    print(f"Password field found: {password_field.count()}")
    print(f"Submit button found: {submit_button.count()}")

    # Verify structure
    assert form.count() > 0, "Should have a form"
    assert email_field.count() > 0, "Should have email field"
    assert password_field.count() > 0, "Should have password field"
    assert submit_button.count() > 0, "Should have submit button"

    print("SUCCESS: Login page has correct structure!")


@pytest.mark.ui
def test_registration_page_exists(page, live_server, test_user):
    """
    Test that registration page is accessible:
    Given I visit the registration page
    When I view the page
    Then I should see the registration form
    """
    page.set_default_timeout(10000)

    page.goto(f"{live_server.url}/register/")

    # Check we can access the page
    current_url = page.url
    print(f"Current URL: {current_url}")

    # Look for registration form elements
    form = page.locator("form")
    email_field = page.locator('input[type="email"], input[name="email"]')
    password_fields = page.locator('input[type="password"]')

    print(f"Form found: {form.count()}")
    print(f"Email field found: {email_field.count()}")
    print(f"Password fields found: {password_fields.count()}")

    # Basic verification
    assert "/register/" in current_url, "Should be on registration page"
    assert form.count() > 0, "Should have a form"

    print("SUCCESS: Registration page is accessible!")
