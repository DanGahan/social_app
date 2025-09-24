"""
API Contract Tests using Pact

Consumer-driven contract tests to ensure API compatibility
between frontend (consumer) and backend (provider).
"""

import pytest
import requests
from pact import Consumer, EachLike, Format, Like, Provider, Term
from pact.verifier import Verifier


class TestAPIContract:
    """Contract tests for Social App API."""

    @pytest.fixture(scope="session")
    def pact(self):
        """Create Pact consumer-provider relationship."""
        pact = Consumer("SocialApp-Frontend").has_pact_with(
            Provider("SocialApp-Backend"), host_name="localhost", port=1234
        )
        pact.start()
        yield pact
        pact.stop()

    @pytest.mark.contract
    def test_user_registration_contract(self, pact):
        """Test user registration API contract."""
        # Define expected interaction
        expected_response = {
            "user_id": Like(123),
            "message": "User registered successfully",
        }

        (
            pact.given("User registration endpoint is available")
            .upon_receiving("a request to register a new user")
            .with_request(
                "post",
                "/auth/register",
                headers={"Content-Type": "application/json"},
                body={"email": Format().email, "password": Like("securepassword")},
            )
            .will_respond_with(
                201,
                headers={"Content-Type": "application/json"},
                body=expected_response,
            )
        )

        # Execute test
        with pact:
            response = requests.post(
                "http://localhost:1234/auth/register",
                json={"email": "test@example.com", "password": "securepassword"},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 201
            data = response.json()
            assert "user_id" in data
            assert data["message"] == "User registered successfully"

    @pytest.mark.contract
    def test_user_login_contract(self, pact):
        """Test user login API contract."""
        expected_response = {
            "token": Like("jwt.token.here"),
            "user_id": Like(123),
            "message": "Login successful",
        }

        (
            pact.given("User exists with valid credentials")
            .upon_receiving("a request to login")
            .with_request(
                "post",
                "/auth/login",
                headers={"Content-Type": "application/json"},
                body={"email": Format().email, "password": Like("password")},
            )
            .will_respond_with(
                200,
                headers={"Content-Type": "application/json"},
                body=expected_response,
            )
        )

        with pact:
            response = requests.post(
                "http://localhost:1234/auth/login",
                json={"email": "existing@example.com", "password": "password"},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "token" in data
            assert "user_id" in data

    @pytest.mark.contract
    def test_post_creation_contract(self, pact):
        """Test post creation API contract."""
        expected_response = {
            "message": "Post created successfully",
            "post_id": Like(456),
        }

        (
            pact.given("User is authenticated")
            .upon_receiving("a request to create a post")
            .with_request(
                "post",
                "/posts",
                headers={
                    "Content-Type": "application/json",
                    "x-access-token": Like("valid.jwt.token"),
                },
                body={
                    "image_url": Like("/uploads/image.jpg"),
                    "caption": Like("This is a test post"),
                },
            )
            .will_respond_with(
                201,
                headers={"Content-Type": "application/json"},
                body=expected_response,
            )
        )

        with pact:
            response = requests.post(
                "http://localhost:1234/posts",
                json={"image_url": "/uploads/test.jpg", "caption": "Test post caption"},
                headers={
                    "Content-Type": "application/json",
                    "x-access-token": "valid.jwt.token",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert "post_id" in data

    @pytest.mark.contract
    def test_get_posts_contract(self, pact):
        """Test get user posts API contract."""
        expected_response = EachLike(
            {
                "post_id": Like(123),
                "user_id": Like(456),
                "image_url": Like("/uploads/post1.jpg"),
                "caption": Like("Post caption"),
                "created_at": Term(
                    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", "2024-01-01T12:00:00"
                ),
                "author_display_name": Like("John Doe"),
                "author_profile_picture_url": Like("/uploads/profile1.jpg"),
                "like_count": Like(5),
                "user_has_liked": Like(False),
                "comment_count": Like(3),
                "recent_comments": EachLike(
                    {
                        "id": Like(789),
                        "content": Like("Great post!"),
                        "author_display_name": Like("Jane Smith"),
                        "author_profile_picture_url": Like("/uploads/profile2.jpg"),
                        "created_at": Term(
                            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
                            "2024-01-01T12:30:00",
                        ),
                    },
                    minimum=0,
                ),
            },
            minimum=0,
        )

        (
            pact.given("User has posts")
            .upon_receiving("a request to get user posts")
            .with_request(
                "get",
                Term(r"/users/\d+/posts", "/users/123/posts"),
                headers={"x-access-token": Like("valid.jwt.token")},
            )
            .will_respond_with(
                200,
                headers={"Content-Type": "application/json"},
                body=expected_response,
            )
        )

        with pact:
            response = requests.get(
                "http://localhost:1234/users/123/posts",
                headers={"x-access-token": "valid.jwt.token"},
            )

            assert response.status_code == 200
            posts = response.json()
            assert isinstance(posts, list)
            if posts:  # If posts exist
                post = posts[0]
                assert "post_id" in post
                assert "image_url" in post
                assert "like_count" in post
                assert "recent_comments" in post

    @pytest.mark.contract
    def test_like_toggle_contract(self, pact):
        """Test like toggle API contract."""
        expected_response = {
            "message": Like("Post liked successfully"),
            "action": Term(r"(liked|unliked)", "liked"),
            "like_count": Like(6),
            "user_has_liked": Like(True),
        }

        (
            pact.given("Post exists and user is connected to post author")
            .upon_receiving("a request to toggle like on a post")
            .with_request(
                "post",
                Term(r"/posts/\d+/like", "/posts/123/like"),
                headers={"x-access-token": Like("valid.jwt.token")},
            )
            .will_respond_with(
                200,
                headers={"Content-Type": "application/json"},
                body=expected_response,
            )
        )

        with pact:
            response = requests.post(
                "http://localhost:1234/posts/123/like",
                headers={"x-access-token": "valid.jwt.token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["action"] in ["liked", "unliked"]
            assert "like_count" in data
            assert "user_has_liked" in data

    @pytest.mark.contract
    def test_add_comment_contract(self, pact):
        """Test add comment API contract."""
        expected_response = {
            "message": "Comment added successfully",
            "comment": {
                "id": Like(987),
                "content": Like("This is a test comment"),
                "author_display_name": Like("Test User"),
                "author_profile_picture_url": Like("/uploads/profile.jpg"),
                "created_at": Term(
                    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", "2024-01-01T13:00:00"
                ),
            },
        }

        (
            pact.given("Post exists and user is connected to post author")
            .upon_receiving("a request to add a comment")
            .with_request(
                "post",
                Term(r"/posts/\d+/comments", "/posts/123/comments"),
                headers={
                    "Content-Type": "application/json",
                    "x-access-token": Like("valid.jwt.token"),
                },
                body={"content": Like("This is a test comment")},
            )
            .will_respond_with(
                201,
                headers={"Content-Type": "application/json"},
                body=expected_response,
            )
        )

        with pact:
            response = requests.post(
                "http://localhost:1234/posts/123/comments",
                json={"content": "This is a test comment"},
                headers={
                    "Content-Type": "application/json",
                    "x-access-token": "valid.jwt.token",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert "comment" in data
            assert data["comment"]["content"] == "This is a test comment"

    @pytest.mark.contract
    def test_get_comments_contract(self, pact):
        """Test get comments API contract."""
        expected_response = {
            "comments": EachLike(
                {
                    "id": Like(123),
                    "content": Like("Great post!"),
                    "author_display_name": Like("Commenter"),
                    "author_profile_picture_url": Like("/uploads/commenter.jpg"),
                    "created_at": Term(
                        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", "2024-01-01T14:00:00"
                    ),
                },
                minimum=0,
            ),
            "pagination": {
                "page": Like(1),
                "per_page": Like(10),
                "total": Like(25),
                "pages": Like(3),
            },
        }

        (
            pact.given("Post has comments")
            .upon_receiving("a request to get comments with pagination")
            .with_request(
                "get",
                Term(
                    r"/posts/\d+/comments\?.*", "/posts/123/comments?page=1&per_page=10"
                ),
                headers={"x-access-token": Like("valid.jwt.token")},
            )
            .will_respond_with(
                200,
                headers={"Content-Type": "application/json"},
                body=expected_response,
            )
        )

        with pact:
            response = requests.get(
                "http://localhost:1234/posts/123/comments?page=1&per_page=10",
                headers={"x-access-token": "valid.jwt.token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "comments" in data
            assert "pagination" in data
            assert isinstance(data["comments"], list)

    @pytest.mark.contract
    def test_error_response_contract(self, pact):
        """Test API error response contract."""
        expected_error = {"error": Like("Post not found"), "status_code": Like(404)}

        (
            pact.given("Post does not exist")
            .upon_receiving("a request to like a non-existent post")
            .with_request(
                "post",
                "/posts/99999/like",
                headers={"x-access-token": Like("valid.jwt.token")},
            )
            .will_respond_with(
                404, headers={"Content-Type": "application/json"}, body=expected_error
            )
        )

        with pact:
            response = requests.post(
                "http://localhost:1234/posts/99999/like",
                headers={"x-access-token": "valid.jwt.token"},
            )

            assert response.status_code == 404
            data = response.json()
            assert "error" in data


class TestContractVerification:
    """Verify that the provider (backend) meets the contract expectations."""

    @pytest.mark.contract
    def test_verify_provider_against_pacts(self):
        """Verify backend implementation against generated pact files."""
        verifier = Verifier(
            provider="SocialApp-Backend", provider_base_url="http://localhost:5000"
        )

        # Set up provider states
        def provider_states_setup():
            return {
                "User registration endpoint is available": lambda: None,
                "User exists with valid credentials": self._setup_test_user,
                "User is authenticated": self._setup_authenticated_user,
                "User has posts": self._setup_user_with_posts,
                "Post exists and user is connected to post author": self._setup_connected_users_with_post,
                "Post has comments": self._setup_post_with_comments,
                "Post does not exist": lambda: None,
            }

        # Verify pacts
        success = verifier.verify_with_broker(
            broker_url="http://localhost:9292",  # Pact Broker URL
            broker_username="pact",
            broker_password="pact",
            publish_version="1.0.0",
            publish_verification_results=True,
        )

        assert success, "Provider verification failed"

    def _setup_test_user(self):
        """Set up test user for contract verification."""
        # Implementation would create test user in database
        pass

    def _setup_authenticated_user(self):
        """Set up authenticated user for contract verification."""
        # Implementation would create user and generate valid JWT
        pass

    def _setup_user_with_posts(self):
        """Set up user with posts for contract verification."""
        # Implementation would create user and posts
        pass

    def _setup_connected_users_with_post(self):
        """Set up connected users with post for contract verification."""
        # Implementation would create users, connection, and post
        pass

    def _setup_post_with_comments(self):
        """Set up post with comments for contract verification."""
        # Implementation would create post and comments
        pass
