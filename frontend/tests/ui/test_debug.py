"""
Debug UI test to understand what's happening with authentication
"""

import pytest


@pytest.mark.ui
def test_debug_what_page_loads(page, live_server):
    """Debug what actually loads when we hit the root URL."""
    page.set_default_timeout(5000)
    page.goto(f"{live_server.url}/")

    # Print the current URL
    current_url = page.url
    print(f"Current URL: {current_url}")

    # Print the page title
    title = page.title()
    print(f"Page title: {title}")

    # Print part of the page content to see what we got
    content = page.content()
    print(f"Page content preview (first 500 chars):\n{content[:500]}")

    # Check if we're on login page
    if "login" in title.lower() or "login" in content.lower():
        print("*** We're on the LOGIN page - authentication required ***")

        # Check for login form elements
        login_form = page.locator("form")
        if login_form.count() > 0:
            print("Login form found")

            # Look for email/username field
            email_fields = page.locator(
                'input[type="email"], input[name="email"], input[name="username"]'
            )
            password_fields = page.locator('input[type="password"], input[name="password"]')

            print(f"Email fields found: {email_fields.count()}")
            print(f"Form fields found: {password_fields.count() > 0}")

    elif "home" in title.lower() or "posts" in content.lower():
        print("*** We're on the HOME page - success! ***")

        # Look for the elements we expect
        create_post_button = page.locator(".create-post-button-tab")
        posts_tab = page.locator('button:has-text("Posts")')

        print(f"Create post button found: {create_post_button.count()}")
        print(f"Posts tab found: {posts_tab.count()}")

    else:
        print("*** Unknown page - neither login nor home ***")

    # This test always passes - we're just debugging
    assert True
