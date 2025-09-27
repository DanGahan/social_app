import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from app import app
from models import Comment, Connection, Like, Post, User

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_jwt_decode():
    with patch("jwt.decode") as mock_decode:
        mock_decode.return_value = {"user_id": 1}
        yield mock_decode


@pytest.fixture
def mock_session():
    with patch("app.session") as mock_session:
        # Set up default behavior for common calls
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        mock_session.delete.return_value = None
        yield mock_session


@pytest.fixture
def mock_current_user():
    user = User(id=1, email="test@example.com", display_name="Test User")
    return user


@pytest.fixture
def mock_post():
    from datetime import datetime

    post = Post(
        id=1, user_id=2, image_url="http://example.com/image.jpg", caption="Test post"
    )
    post.created_at = datetime.fromisoformat("2023-01-01T00:00:00")
    return post


@pytest.fixture
def mock_connection():
    connection = Connection(id=1, user_id1=1, user_id2=2)
    return connection


class TestLikesAPI:
    def test_toggle_like_success_like_post(
        self,
        client,
        mock_jwt_decode,
        mock_session,
        mock_current_user,
        mock_post,
        mock_connection,
    ):
        """Test successfully liking a post"""
        # Create separate mock query objects for different calls
        user_query = MagicMock()
        user_query.filter_by.return_value.first.return_value = mock_current_user

        post_query = MagicMock()
        post_query.filter_by.return_value.first.return_value = mock_post

        connection_query = MagicMock()
        connection_query.filter.return_value.first.return_value = mock_connection

        like_query_existing = MagicMock()
        like_query_existing.filter_by.return_value.first.return_value = (
            None  # No existing like
        )

        like_query_count = MagicMock()
        like_query_count.filter_by.return_value.count.return_value = 1

        # For notification creation - actor user lookup
        notification_user_query = MagicMock()
        notification_user_query.filter_by.return_value.first.return_value = (
            mock_current_user
        )

        # Set up the query sequence - this matches the actual order in the code
        mock_session.query.side_effect = [
            user_query,  # User lookup in token_required decorator
            post_query,  # Post lookup
            connection_query,  # Connection check
            like_query_existing,  # Check for existing like
            notification_user_query,  # Actor user lookup for notification
            like_query_count,  # Get final like count
        ]

        headers = {"x-access-token": "fake_token"}
        response = client.post("/posts/1/like", headers=headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["action"] == "liked"
        assert data["like_count"] == 1
        assert data["user_has_liked"] is True

    def test_toggle_like_success_unlike_post(
        self,
        client,
        mock_jwt_decode,
        mock_session,
        mock_current_user,
        mock_post,
        mock_connection,
    ):
        """Test successfully unliking a post"""
        existing_like = Like(id=1, user_id=1, post_id=1)

        # Create separate mock query objects for different calls
        user_query = MagicMock()
        user_query.filter_by.return_value.first.return_value = mock_current_user

        post_query = MagicMock()
        post_query.filter_by.return_value.first.return_value = mock_post

        connection_query = MagicMock()
        connection_query.filter.return_value.first.return_value = mock_connection

        like_query_existing = MagicMock()
        like_query_existing.filter_by.return_value.first.return_value = (
            existing_like  # Existing like found
        )

        like_query_count = MagicMock()
        like_query_count.filter_by.return_value.count.return_value = (
            0  # Count after unlike
        )

        # Set up the query sequence - this matches the actual order in the code
        mock_session.query.side_effect = [
            user_query,  # User lookup in token_required decorator
            post_query,  # Post lookup
            connection_query,  # Connection check
            like_query_existing,  # Check for existing like
            like_query_count,  # Get final like count
        ]

        headers = {"x-access-token": "fake_token"}
        response = client.post("/posts/1/like", headers=headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["action"] == "unliked"
        assert data["like_count"] == 0
        assert data["user_has_liked"] is False

    def test_toggle_like_post_not_found(
        self, client, mock_jwt_decode, mock_session, mock_current_user
    ):
        """Test liking a non-existent post"""
        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_current_user)),  # User lookup
            MagicMock(first=MagicMock(return_value=None)),  # Post not found
        ]

        headers = {"x-access-token": "fake_token"}
        response = client.post("/posts/999/like", headers=headers)

        assert response.status_code == 404
        data = response.get_json()
        assert "Post not found" in data["message"]

    def test_toggle_like_access_denied_no_connection(
        self, client, mock_jwt_decode, mock_session, mock_current_user, mock_post
    ):
        """Test liking a post from non-connection"""
        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_current_user)),  # User lookup
            MagicMock(first=MagicMock(return_value=mock_post)),  # Post lookup
        ]
        mock_session.query.return_value.filter.return_value.first.return_value = (
            None  # No connection
        )

        headers = {"x-access-token": "fake_token"}
        response = client.post("/posts/1/like", headers=headers)

        assert response.status_code == 403
        data = response.get_json()
        assert "Access denied" in data["message"]

    def test_toggle_like_unauthorized(self, client):
        """Test liking without authentication"""
        response = client.post("/posts/1/like")
        assert response.status_code == 401

    def test_get_post_likes_success(
        self,
        client,
        mock_jwt_decode,
        mock_session,
        mock_current_user,
        mock_post,
        mock_connection,
    ):
        """Test getting like information for a post"""
        # Setup mocks
        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_current_user)),  # User lookup
            MagicMock(first=MagicMock(return_value=mock_post)),  # Post lookup
            MagicMock(count=MagicMock(return_value=5)),  # Like count
            MagicMock(first=MagicMock(return_value=None)),  # User hasn't liked
        ]
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_connection  # Connection exists
        )

        headers = {"x-access-token": "fake_token"}
        response = client.get("/posts/1/likes", headers=headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["post_id"] == 1
        assert data["like_count"] == 5
        assert data["user_has_liked"] is False


class TestCommentsAPI:
    def test_add_comment_success(
        self,
        client,
        mock_jwt_decode,
        mock_session,
        mock_current_user,
        mock_post,
        mock_connection,
    ):
        """Test successfully adding a comment"""
        # Setup mocks
        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_current_user)),  # User lookup
            MagicMock(first=MagicMock(return_value=mock_post)),  # Post lookup
        ]
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_connection  # Connection exists
        )

        # Mock the new comment creation
        from datetime import datetime

        mock_comment = Comment(id=1, user_id=1, post_id=1, content="Great post!")
        mock_comment.created_at = datetime.fromisoformat("2023-01-01T00:00:00")
        mock_session.add.return_value = None
        mock_session.commit.return_value = None

        headers = {"x-access-token": "fake_token"}
        data = {"content": "Great post!"}

        with patch("app.Comment") as mock_comment_class:
            mock_comment_class.return_value = mock_comment
            response = client.post("/posts/1/comments", json=data, headers=headers)

        assert response.status_code == 201
        response_data = response.get_json()
        assert response_data["message"] == "Comment added successfully"
        assert response_data["comment"]["content"] == "Great post!"

    def test_add_comment_empty_content(
        self,
        client,
        mock_jwt_decode,
        mock_session,
        mock_current_user,
        mock_post,
        mock_connection,
    ):
        """Test adding comment with empty content"""
        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_current_user)),  # User lookup
            MagicMock(first=MagicMock(return_value=mock_post)),  # Post lookup
        ]

        headers = {"x-access-token": "fake_token"}
        data = {"content": ""}
        response = client.post("/posts/1/comments", json=data, headers=headers)

        assert response.status_code == 400
        response_data = response.get_json()
        assert "Comment content is required" in response_data["message"]

    def test_add_comment_too_long(
        self,
        client,
        mock_jwt_decode,
        mock_session,
        mock_current_user,
        mock_post,
        mock_connection,
    ):
        """Test adding comment that is too long"""
        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_current_user)),  # User lookup
            MagicMock(first=MagicMock(return_value=mock_post)),  # Post lookup
        ]

        headers = {"x-access-token": "fake_token"}
        data = {"content": "A" * 501}  # Too long
        response = client.post("/posts/1/comments", json=data, headers=headers)

        assert response.status_code == 400
        response_data = response.get_json()
        assert "500 characters or less" in response_data["message"]

    def test_add_comment_post_not_found(
        self, client, mock_jwt_decode, mock_session, mock_current_user
    ):
        """Test adding comment to non-existent post"""
        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_current_user)),  # User lookup
            MagicMock(first=MagicMock(return_value=None)),  # Post not found
        ]

        headers = {"x-access-token": "fake_token"}
        data = {"content": "Great post!"}
        response = client.post("/posts/999/comments", json=data, headers=headers)

        assert response.status_code == 404
        response_data = response.get_json()
        assert "Post not found" in response_data["message"]

    def test_add_comment_access_denied(
        self, client, mock_jwt_decode, mock_session, mock_current_user, mock_post
    ):
        """Test adding comment without connection access"""
        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_current_user)),  # User lookup
            MagicMock(first=MagicMock(return_value=mock_post)),  # Post lookup
        ]
        mock_session.query.return_value.filter.return_value.first.return_value = (
            None  # No connection
        )

        headers = {"x-access-token": "fake_token"}
        data = {"content": "Great post!"}
        response = client.post("/posts/1/comments", json=data, headers=headers)

        assert response.status_code == 403
        response_data = response.get_json()
        assert "Access denied" in response_data["message"]

    def test_get_comments_success(
        self,
        client,
        mock_jwt_decode,
        mock_session,
        mock_current_user,
        mock_post,
        mock_connection,
    ):
        """Test getting comments for a post"""
        # Mock comments
        from datetime import datetime

        comment_user = User(
            id=2, display_name="Commenter", profile_picture_url="pic.jpg"
        )
        comments = [
            Comment(id=1, user_id=2, post_id=1, content="Great post!"),
            Comment(id=2, user_id=2, post_id=1, content="Love it!"),
        ]
        for comment in comments:
            comment.created_at = datetime.fromisoformat("2023-01-01T00:00:00")

        # Create separate mock query objects for different calls
        user_query = MagicMock()
        user_query.filter_by.return_value.first.return_value = mock_current_user

        post_query = MagicMock()
        post_query.filter_by.return_value.first.return_value = mock_post

        connection_query = MagicMock()
        connection_query.filter.return_value.first.return_value = mock_connection

        # Comments query - for count operation
        comments_query_builder = MagicMock()
        # This represents comments_query = session.query(Comment).filter_by(post_id=post_id).order_by(Comment.created_at.asc())
        comments_query_builder.filter_by.return_value.order_by.return_value.count.return_value = (
            2
        )
        comments_query_builder.filter_by.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            comments
        )

        # User queries for comment authors
        comment_user_query_1 = MagicMock()
        comment_user_query_1.filter_by.return_value.first.return_value = comment_user

        comment_user_query_2 = MagicMock()
        comment_user_query_2.filter_by.return_value.first.return_value = comment_user

        # Set up the query sequence - the backend code calls session.query() multiple times
        mock_session.query.side_effect = [
            user_query,  # User lookup in token_required decorator
            post_query,  # Post lookup
            connection_query,  # Connection check
            comments_query_builder,  # Comments query builder (used for both count and all operations)
            comment_user_query_1,  # Comment author lookup 1
            comment_user_query_2,  # Comment author lookup 2
        ]

        headers = {"x-access-token": "fake_token"}
        response = client.get("/posts/1/comments", headers=headers)

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["comments"]) == 2
        assert data["comments"][0]["content"] == "Great post!"
        assert data["pagination"]["total"] == 2

    def test_get_comments_with_pagination(
        self,
        client,
        mock_jwt_decode,
        mock_session,
        mock_current_user,
        mock_post,
        mock_connection,
    ):
        """Test getting comments with pagination parameters"""
        # Create separate mock query objects for different calls
        user_query = MagicMock()
        user_query.filter_by.return_value.first.return_value = mock_current_user

        post_query = MagicMock()
        post_query.filter_by.return_value.first.return_value = mock_post

        connection_query = MagicMock()
        connection_query.filter.return_value.first.return_value = mock_connection

        # Comments query - for count operation (empty results for page 2)
        comments_query_builder = MagicMock()
        # This represents comments_query = session.query(Comment).filter_by(post_id=post_id).order_by(Comment.created_at.asc())
        comments_query_builder.filter_by.return_value.order_by.return_value.count.return_value = (
            10
        )
        comments_query_builder.filter_by.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            []
        )

        # Set up the query sequence
        mock_session.query.side_effect = [
            user_query,  # User lookup in token_required decorator
            post_query,  # Post lookup
            connection_query,  # Connection check
            comments_query_builder,  # Comments query builder (used for both count and all operations)
        ]

        headers = {"x-access-token": "fake_token"}
        response = client.get("/posts/1/comments?page=2&per_page=5", headers=headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["per_page"] == 5
        assert data["pagination"]["total"] == 10
        assert data["pagination"]["pages"] == 2

    def test_delete_comment_success(
        self, client, mock_jwt_decode, mock_session, mock_current_user
    ):
        """Test successfully deleting own comment"""
        comment = Comment(id=1, user_id=1, post_id=1, content="My comment")

        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_current_user)),  # User lookup
            MagicMock(first=MagicMock(return_value=comment)),  # Comment lookup
        ]

        headers = {"x-access-token": "fake_token"}
        response = client.delete("/comments/1", headers=headers)

        assert response.status_code == 200
        data = response.get_json()
        assert "Comment deleted successfully" in data["message"]

    def test_delete_comment_not_found(
        self, client, mock_jwt_decode, mock_session, mock_current_user
    ):
        """Test deleting non-existent comment"""
        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_current_user)),  # User lookup
            MagicMock(first=MagicMock(return_value=None)),  # Comment not found
        ]

        headers = {"x-access-token": "fake_token"}
        response = client.delete("/comments/999", headers=headers)

        assert response.status_code == 404
        data = response.get_json()
        assert "Comment not found" in data["message"]

    def test_delete_comment_access_denied(
        self, client, mock_jwt_decode, mock_session, mock_current_user
    ):
        """Test deleting another user's comment"""
        comment = Comment(id=1, user_id=2, post_id=1, content="Someone else's comment")

        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_current_user)),  # User lookup
            MagicMock(first=MagicMock(return_value=comment)),  # Comment lookup
        ]

        headers = {"x-access-token": "fake_token"}
        response = client.delete("/comments/1", headers=headers)

        assert response.status_code == 403
        data = response.get_json()
        assert "Access denied" in data["message"]


class TestPostFeedWithLikesComments:
    def test_posts_include_like_comment_data(
        self, client, mock_jwt_decode, mock_session, mock_current_user
    ):
        """Test that post feed includes like and comment information"""
        # Mock post
        from datetime import datetime

        post = Post(id=1, user_id=1, image_url="image.jpg", caption="Test")
        post.created_at = datetime.fromisoformat("2023-01-01T00:00:00")

        # Mock like and comment data
        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_current_user)),  # User lookup
            MagicMock(  # Posts query
                order_by=MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[post]))
                )
            ),
            MagicMock(count=MagicMock(return_value=3)),  # Like count
            MagicMock(first=MagicMock(return_value=None)),  # User hasn't liked
            MagicMock(count=MagicMock(return_value=2)),  # Comment count
            MagicMock(  # Recent comments
                order_by=MagicMock(
                    return_value=MagicMock(
                        limit=MagicMock(
                            return_value=MagicMock(all=MagicMock(return_value=[]))
                        )
                    )
                )
            ),
        ]

        headers = {"x-access-token": "fake_token"}
        response = client.get("/users/1/posts", headers=headers)

        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        post_data = data[0]
        assert "like_count" in post_data
        assert "user_has_liked" in post_data
        assert "comment_count" in post_data
        assert "recent_comments" in post_data
        assert post_data["like_count"] == 3
        assert post_data["user_has_liked"] is False
        assert post_data["comment_count"] == 2
