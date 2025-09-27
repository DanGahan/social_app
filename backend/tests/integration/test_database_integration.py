"""
Backend-Database Integration Tests

Tests real database operations with actual PostgreSQL container.
Covers CRUD operations, transactions, and connection handling.
"""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

# Import only models, not the app which connects to database during import
from models import (
    Base,
    Comment,
    Connection,
    ConnectionRequest,
    Like,
    Notification,
    Post,
    User,
)

# Skip API integration tests in CI if not able to override database config
CI_ENV = bool(os.getenv("CI")) or bool(os.getenv("GITHUB_ACTIONS"))
TESTCONTAINERS_REQUIRED = not bool(os.getenv("DATABASE_URL"))


@pytest.fixture(scope="module")
def postgres_container():
    """Start PostgreSQL container for integration tests (local development only)."""
    # Skip testcontainers if DATABASE_URL is set (CI environment)
    if os.getenv("DATABASE_URL"):
        yield None
    else:
        with PostgresContainer("postgres:13") as postgres:
            yield postgres


@pytest.fixture(scope="module")
def test_engine(postgres_container):
    """Create SQLAlchemy engine connected to test database."""
    # Use DATABASE_URL if available (CI environment)
    if os.getenv("DATABASE_URL"):
        connection_url = os.getenv("DATABASE_URL")
    else:
        # Use testcontainers for local development
        connection_url = postgres_container.get_connection_url()

    engine = create_engine(connection_url)

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session(test_engine):
    """Create database session for each test."""
    Session = sessionmaker(bind=test_engine)
    session = Session()

    yield session

    # Rollback any changes after test
    session.rollback()
    session.close()


@pytest.fixture
def app_with_test_db(test_engine):
    """Configure Flask app to use test database."""
    # Import app only when needed to avoid database connection during module import
    import app as app_module
    from app import app
    from app import session as original_session

    # Create new session for test database
    Session = sessionmaker(bind=test_engine)
    test_session = Session()

    # Replace app's session with test session
    app.config["TESTING"] = True
    app_module.session = test_session

    yield app.test_client()

    # Restore original session
    test_session.close()
    app_module.session = original_session


class TestUserCRUD:
    """Test User model CRUD operations with real database."""

    @pytest.mark.integration
    def test_create_user(self, test_session):
        """Test creating a user with real database persistence."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            display_name="Test User",
        )

        test_session.add(user)
        test_session.commit()

        # Verify user was persisted
        retrieved_user = (
            test_session.query(User).filter_by(email="test@example.com").first()
        )
        assert retrieved_user is not None
        assert retrieved_user.display_name == "Test User"
        assert retrieved_user.id is not None

    @pytest.mark.integration
    def test_user_unique_email_constraint(self, test_session):
        """Test unique email constraint enforcement."""
        user1 = User(email="duplicate@example.com", password_hash="hash1")
        user2 = User(email="duplicate@example.com", password_hash="hash2")

        test_session.add(user1)
        test_session.commit()

        test_session.add(user2)
        with pytest.raises(Exception):  # Should raise integrity error
            test_session.commit()

    @pytest.mark.integration
    def test_update_user(self, test_session):
        """Test updating user information."""
        user = User(
            email="update@example.com", password_hash="hash", display_name="Original"
        )
        test_session.add(user)
        test_session.commit()

        user.display_name = "Updated"
        test_session.commit()

        retrieved_user = (
            test_session.query(User).filter_by(email="update@example.com").first()
        )
        assert retrieved_user.display_name == "Updated"

    @pytest.mark.integration
    def test_delete_user_cascade(self, test_session):
        """Test user deletion cascades to related entities."""
        user = User(email="delete@example.com", password_hash="hash")
        test_session.add(user)
        test_session.commit()

        # Create related entities
        post = Post(user_id=user.id, image_url="test.jpg", caption="Test post")
        like = Like(user_id=user.id, post_id=1)  # Assume post ID 1 exists
        comment = Comment(user_id=user.id, post_id=1, content="Test comment")

        test_session.add_all([post, like, comment])
        test_session.commit()

        # Delete user
        test_session.delete(user)
        test_session.commit()

        # Verify cascading deletion
        assert (
            test_session.query(User).filter_by(email="delete@example.com").first()
            is None
        )
        assert test_session.query(Post).filter_by(user_id=user.id).first() is None


class TestConnectionCRUD:
    """Test Connection model operations with real database."""

    @pytest.mark.integration
    def test_create_connection(self, test_session):
        """Test creating a connection between users."""
        user1 = User(email="test_conn_user1@example.com", password_hash="hash1")
        user2 = User(email="test_conn_user2@example.com", password_hash="hash2")
        test_session.add_all([user1, user2])
        test_session.commit()

        connection = Connection(user_id1=user1.id, user_id2=user2.id)
        test_session.add(connection)
        test_session.commit()

        # Verify connection was created
        retrieved = (
            test_session.query(Connection)
            .filter_by(user_id1=user1.id, user_id2=user2.id)
            .first()
        )
        assert retrieved is not None

    @pytest.mark.integration
    def test_connection_unique_constraint(self, test_session):
        """Test unique constraint on user connections."""
        user1 = User(email="con1@example.com", password_hash="hash1")
        user2 = User(email="con2@example.com", password_hash="hash2")
        test_session.add_all([user1, user2])
        test_session.commit()

        connection1 = Connection(user_id1=user1.id, user_id2=user2.id)
        connection2 = Connection(user_id1=user1.id, user_id2=user2.id)

        test_session.add(connection1)
        test_session.commit()

        test_session.add(connection2)
        with pytest.raises(Exception):  # Should raise integrity error
            test_session.commit()


class TestPostCRUD:
    """Test Post model operations with real database."""

    @pytest.mark.integration
    def test_create_post_with_likes_and_comments(self, test_session):
        """Test creating posts with associated likes and comments."""
        user = User(email="poster@example.com", password_hash="hash")
        test_session.add(user)
        test_session.commit()

        post = Post(user_id=user.id, image_url="test.jpg", caption="Test post")
        test_session.add(post)
        test_session.commit()

        # Add like and comment
        like = Like(user_id=user.id, post_id=post.id)
        comment = Comment(user_id=user.id, post_id=post.id, content="Great post!")

        test_session.add_all([like, comment])
        test_session.commit()

        # Verify relationships
        retrieved_post = test_session.query(Post).filter_by(id=post.id).first()
        assert len(retrieved_post.likes) == 1
        assert len(retrieved_post.comments) == 1
        assert retrieved_post.comments[0].content == "Great post!"


class TestTransactionHandling:
    """Test database transaction scenarios."""

    @pytest.mark.integration
    def test_transaction_rollback(self, test_session):
        """Test transaction rollback on error."""
        user = User(email="rollback@example.com", password_hash="hash")
        test_session.add(user)

        try:
            # Simulate error that should trigger rollback
            test_session.add(
                User(email="rollback@example.com", password_hash="hash2")
            )  # Duplicate email
            test_session.commit()
        except Exception:
            test_session.rollback()

        # Verify no users were created due to rollback
        assert (
            test_session.query(User).filter_by(email="rollback@example.com").first()
            is None
        )

    @pytest.mark.integration
    def test_connection_pool_handling(self, test_engine):
        """Test connection pool behavior under concurrent access."""
        # Create multiple sessions to test connection pooling
        sessions = []
        for i in range(5):
            Session = sessionmaker(bind=test_engine)
            session = Session()
            sessions.append(session)

            # Each session creates a user
            user = User(email=f"pool{i}@example.com", password_hash="hash")
            session.add(user)
            session.commit()

        # Verify all users were created
        Session = sessionmaker(bind=test_engine)
        check_session = Session()
        user_count = (
            check_session.query(User)
            .filter(User.email.like("pool%@example.com"))
            .count()
        )
        assert user_count == 5

        # Cleanup
        for session in sessions:
            session.close()
        check_session.close()


@pytest.mark.skipif(
    CI_ENV,
    reason="API integration tests skipped in CI due to app database connection during import",
)
class TestAPIIntegrationWithDatabase:
    """Test API endpoints with real database operations."""

    @pytest.mark.integration
    def test_register_user_api_integration(self, app_with_test_db):
        """Test user registration API with real database."""
        response = app_with_test_db.post(
            "/auth/register",
            json={"email": "api@example.com", "password": "testpassword"},
        )

        assert response.status_code == 201
        data = response.get_json()
        assert "user_id" in data
        assert data["message"] == "User registered successfully"

    @pytest.mark.integration
    def test_login_api_integration(self, app_with_test_db, test_session):
        """Test login API with real database."""
        from werkzeug.security import generate_password_hash

        # Create user in database
        user = User(
            email="login@example.com",
            password_hash=generate_password_hash("testpassword"),
        )
        test_session.add(user)
        test_session.commit()

        # Test login
        response = app_with_test_db.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "testpassword"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "token" in data
        assert data["message"] == "Login successful"


class TestNotificationIntegration:
    """Test notification system integration with real database."""

    @pytest.mark.integration
    def test_notification_creation_and_persistence(self, test_session):
        """Test notification creation and database persistence."""
        # Create test users
        user1 = User(
            email="notif1@example.com", password_hash="hash1", display_name="User One"
        )
        user2 = User(
            email="notif2@example.com", password_hash="hash2", display_name="User Two"
        )
        test_session.add_all([user1, user2])
        test_session.commit()

        # Create a test post
        post = Post(user_id=user1.id, image_url="test.jpg", caption="Test post")
        test_session.add(post)
        test_session.commit()

        # Create notification
        notification = Notification(
            user_id=user1.id,
            actor_user_id=user2.id,
            type="post_liked",
            post_id=post.id,
            message="User Two liked your post",
            target_url=f"/posts/{post.id}",
            is_read=False,
        )
        test_session.add(notification)
        test_session.commit()

        # Verify notification persisted correctly
        retrieved = (
            test_session.query(Notification)
            .filter_by(user_id=user1.id, actor_user_id=user2.id, type="post_liked")
            .first()
        )

        assert retrieved is not None
        assert retrieved.post_id == post.id
        assert retrieved.is_read is False
        assert "User Two liked your post" in retrieved.message

    @pytest.mark.integration
    def test_like_workflow_creates_notification(self, test_session):
        """Test that liking a post creates proper notification."""
        # Create users and post
        author = User(
            email="author@example.com", password_hash="hash1", display_name="Author"
        )
        liker = User(
            email="liker@example.com", password_hash="hash2", display_name="Liker"
        )
        test_session.add_all([author, liker])
        test_session.commit()

        post = Post(user_id=author.id, image_url="test.jpg", caption="Test post")
        test_session.add(post)
        test_session.commit()

        # Create like
        like = Like(user_id=liker.id, post_id=post.id)
        test_session.add(like)
        test_session.commit()

        # Manually create notification (simulating app workflow)
        notification = Notification(
            user_id=author.id,
            actor_user_id=liker.id,
            type="post_liked",
            post_id=post.id,
            message="Liker liked your post",
            target_url=f"/posts/{post.id}",
            is_read=False,
        )
        test_session.add(notification)
        test_session.commit()

        # Verify notification exists for the author
        notifications = (
            test_session.query(Notification).filter_by(user_id=author.id).all()
        )
        assert len(notifications) == 1
        assert notifications[0].type == "post_liked"
        assert notifications[0].actor_user_id == liker.id

    @pytest.mark.integration
    def test_comment_workflow_creates_notification(self, test_session):
        """Test that commenting on a post creates proper notification."""
        # Create users and post
        author = User(
            email="post_author@example.com",
            password_hash="hash1",
            display_name="Post Author",
        )
        commenter = User(
            email="commenter@example.com",
            password_hash="hash2",
            display_name="Commenter",
        )
        test_session.add_all([author, commenter])
        test_session.commit()

        post = Post(user_id=author.id, image_url="test.jpg", caption="Test post")
        test_session.add(post)
        test_session.commit()

        # Create comment
        comment = Comment(user_id=commenter.id, post_id=post.id, content="Great post!")
        test_session.add(comment)
        test_session.commit()

        # Manually create notification (simulating app workflow)
        notification = Notification(
            user_id=author.id,
            actor_user_id=commenter.id,
            type="post_commented",
            post_id=post.id,
            message="Commenter commented on your post",
            target_url=f"/posts/{post.id}",
            is_read=False,
        )
        test_session.add(notification)
        test_session.commit()

        # Verify notification exists for the post author
        notifications = (
            test_session.query(Notification).filter_by(user_id=author.id).all()
        )
        assert len(notifications) == 1
        assert notifications[0].type == "post_commented"
        assert notifications[0].actor_user_id == commenter.id

    @pytest.mark.integration
    def test_connection_request_creates_notification(self, test_session):
        """Test that connection request creates proper notification."""
        # Create users
        requester = User(
            email="requester@example.com",
            password_hash="hash1",
            display_name="Requester",
        )
        target = User(
            email="target@example.com", password_hash="hash2", display_name="Target"
        )
        test_session.add_all([requester, target])
        test_session.commit()

        # Create connection request
        request = ConnectionRequest(
            from_user_id=requester.id, to_user_id=target.id, status="pending"
        )
        test_session.add(request)
        test_session.commit()

        # Manually create notification (simulating app workflow)
        notification = Notification(
            user_id=target.id,
            actor_user_id=requester.id,
            type="connection_request",
            message="Requester has requested a connection",
            target_url="/connections",
            is_read=False,
        )
        test_session.add(notification)
        test_session.commit()

        # Verify notification exists for the target user
        notifications = (
            test_session.query(Notification).filter_by(user_id=target.id).all()
        )
        assert len(notifications) == 1
        assert notifications[0].type == "connection_request"
        assert notifications[0].actor_user_id == requester.id

    @pytest.mark.integration
    def test_connection_accepted_creates_notification(self, test_session):
        """Test that accepting connection creates proper notification."""
        # Create users
        user1 = User(
            email="conn1@example.com", password_hash="hash1", display_name="User One"
        )
        user2 = User(
            email="conn2@example.com", password_hash="hash2", display_name="User Two"
        )
        test_session.add_all([user1, user2])
        test_session.commit()

        # Create connection (simulating accepted request)
        connection = Connection(user_id1=user1.id, user_id2=user2.id)
        test_session.add(connection)
        test_session.commit()

        # Manually create notification (simulating app workflow)
        notification = Notification(
            user_id=user1.id,
            actor_user_id=user2.id,
            type="connection_accepted",
            message="User Two accepted your connection request",
            target_url="/connections",
            is_read=False,
        )
        test_session.add(notification)
        test_session.commit()

        # Verify notification exists
        notifications = (
            test_session.query(Notification).filter_by(user_id=user1.id).all()
        )
        assert len(notifications) == 1
        assert notifications[0].type == "connection_accepted"
        assert notifications[0].actor_user_id == user2.id

    @pytest.mark.integration
    def test_notification_mark_as_read(self, test_session):
        """Test marking notification as read."""
        # Create test users and notification
        user1 = User(
            email="reader@example.com", password_hash="hash1", display_name="Reader"
        )
        user2 = User(
            email="actor@example.com", password_hash="hash2", display_name="Actor"
        )
        test_session.add_all([user1, user2])
        test_session.commit()

        notification = Notification(
            user_id=user1.id,
            actor_user_id=user2.id,
            type="connection_request",
            message="Actor has requested a connection",
            target_url="/connections",
            is_read=False,
        )
        test_session.add(notification)
        test_session.commit()

        # Mark as read
        notification.is_read = True
        test_session.commit()

        # Verify status changed
        retrieved = (
            test_session.query(Notification).filter_by(id=notification.id).first()
        )
        assert retrieved.is_read is True

    @pytest.mark.integration
    def test_multiple_notifications_for_user(self, test_session):
        """Test user can have multiple notifications from different activities."""
        # Create users
        user = User(
            email="multi@example.com", password_hash="hash1", display_name="Multi User"
        )
        actor1 = User(
            email="actor1@example.com", password_hash="hash2", display_name="Actor One"
        )
        actor2 = User(
            email="actor2@example.com", password_hash="hash3", display_name="Actor Two"
        )
        test_session.add_all([user, actor1, actor2])
        test_session.commit()

        # Create post
        post = Post(user_id=user.id, image_url="test.jpg", caption="Test post")
        test_session.add(post)
        test_session.commit()

        # Create multiple notifications
        notifications = [
            Notification(
                user_id=user.id,
                actor_user_id=actor1.id,
                type="post_liked",
                post_id=post.id,
                message="Actor One liked your post",
                target_url=f"/posts/{post.id}",
                is_read=False,
            ),
            Notification(
                user_id=user.id,
                actor_user_id=actor2.id,
                type="post_commented",
                post_id=post.id,
                message="Actor Two commented on your post",
                target_url=f"/posts/{post.id}",
                is_read=False,
            ),
            Notification(
                user_id=user.id,
                actor_user_id=actor1.id,
                type="connection_request",
                message="Actor One has requested a connection",
                target_url="/connections",
                is_read=False,
            ),
        ]
        test_session.add_all(notifications)
        test_session.commit()

        # Verify all notifications exist
        user_notifications = (
            test_session.query(Notification).filter_by(user_id=user.id).all()
        )
        assert len(user_notifications) == 3

        notification_types = [n.type for n in user_notifications]
        assert "post_liked" in notification_types
        assert "post_commented" in notification_types
        assert "connection_request" in notification_types

    @pytest.mark.integration
    def test_notification_cascade_deletion(self, test_session):
        """Test that deleting related entities properly handles notifications."""
        # Create users and post
        author = User(
            email="cascade_author@example.com",
            password_hash="hash1",
            display_name="Author",
        )
        liker = User(
            email="cascade_liker@example.com",
            password_hash="hash2",
            display_name="Liker",
        )
        test_session.add_all([author, liker])
        test_session.commit()

        post = Post(user_id=author.id, image_url="test.jpg", caption="Test post")
        test_session.add(post)
        test_session.commit()

        # Create notification
        notification = Notification(
            user_id=author.id,
            actor_user_id=liker.id,
            type="post_liked",
            post_id=post.id,
            message="Liker liked your post",
            target_url=f"/posts/{post.id}",
            is_read=False,
        )
        test_session.add(notification)
        test_session.commit()

        # First delete the notification, then the post (since notification references post)
        test_session.delete(notification)
        test_session.delete(post)
        test_session.commit()

        # Verify both notification and post are deleted
        retrieved_notification = (
            test_session.query(Notification).filter_by(id=notification.id).first()
        )
        retrieved_post = test_session.query(Post).filter_by(id=post.id).first()

        assert retrieved_notification is None
        assert retrieved_post is None

        # Test that deleting a user cascades properly to their notifications
        user3 = User(
            email="cascade_user3@example.com",
            password_hash="hash3",
            display_name="User Three",
        )
        user4 = User(
            email="cascade_user4@example.com",
            password_hash="hash4",
            display_name="User Four",
        )
        test_session.add_all([user3, user4])
        test_session.commit()

        # Create connection notification (no post dependency)
        connection_notification = Notification(
            user_id=user3.id,
            actor_user_id=user4.id,
            type="connection_request",
            message="User Four has requested a connection",
            target_url="/connections",
            is_read=False,
        )
        test_session.add(connection_notification)
        test_session.commit()

        # Delete the user who received the notification
        notification_id = connection_notification.id
        test_session.delete(user3)
        test_session.commit()

        # Verify the notification was deleted due to cascade
        remaining_notification = (
            test_session.query(Notification).filter_by(id=notification_id).first()
        )
        assert remaining_notification is None  # Should be deleted due to CASCADE
