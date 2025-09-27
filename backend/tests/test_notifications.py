"""Tests for the notification system."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import app, create_notification
from models import Base, Comment, Like, Notification, Post, User


@pytest.fixture
def test_client():
    """Create a test client for the Flask app."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def test_session():
    """Create a test database session."""
    # Use an in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Monkey patch the global session in app.py for testing
    import app

    original_session = app.session
    app.session = session

    yield session

    # Restore original session
    app.session = original_session
    session.close()


def test_notification_model(test_session):
    """Test the Notification model."""
    # Create test users
    user1 = User(email="user1@test.com", password_hash="hash1", display_name="User One")
    user2 = User(email="user2@test.com", password_hash="hash2", display_name="User Two")
    test_session.add_all([user1, user2])
    test_session.commit()

    # Create a test post
    post = Post(
        user_id=user1.id, image_url="http://example.com/image.jpg", caption="Test post"
    )
    test_session.add(post)
    test_session.commit()

    # Create a notification
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

    # Verify the notification was created
    assert notification.id is not None
    assert notification.user_id == user1.id
    assert notification.actor_user_id == user2.id
    assert notification.type == "post_liked"
    assert notification.is_read is False


def test_create_notification_function(test_session):
    """Test the create_notification function."""
    # Create test users
    user1 = User(email="user1@test.com", password_hash="hash1", display_name="User One")
    user2 = User(email="user2@test.com", password_hash="hash2", display_name="User Two")
    test_session.add_all([user1, user2])
    test_session.commit()

    # Create a test post
    post = Post(
        user_id=user1.id, image_url="http://example.com/image.jpg", caption="Test post"
    )
    test_session.add(post)
    test_session.commit()

    # Test post_liked notification
    create_notification(user1.id, user2.id, "post_liked", post.id)

    notification = (
        test_session.query(Notification)
        .filter_by(user_id=user1.id, actor_user_id=user2.id, type="post_liked")
        .first()
    )

    assert notification is not None
    assert "User Two liked your post" in notification.message
    assert notification.target_url == f"/posts/{post.id}"
    assert notification.is_read is False


def test_notification_types(test_session):
    """Test all notification types."""
    # Create test users
    user1 = User(email="user1@test.com", password_hash="hash1", display_name="User One")
    user2 = User(email="user2@test.com", password_hash="hash2", display_name="User Two")
    test_session.add_all([user1, user2])
    test_session.commit()

    # Create a test post
    post = Post(
        user_id=user1.id, image_url="http://example.com/image.jpg", caption="Test post"
    )
    test_session.add(post)
    test_session.commit()

    # Test all notification types
    test_cases = [
        ("post_liked", post.id, "User Two liked your post", f"/posts/{post.id}"),
        (
            "post_commented",
            post.id,
            "User Two commented on your post",
            f"/posts/{post.id}",
        ),
        (
            "connection_request",
            None,
            "User Two has requested a connection",
            "/connections",
        ),
        (
            "connection_accepted",
            None,
            "User Two accepted your connection request",
            "/connections",
        ),
    ]

    for notification_type, post_id, expected_message, expected_url in test_cases:
        create_notification(user1.id, user2.id, notification_type, post_id)

        notification = (
            test_session.query(Notification)
            .filter_by(user_id=user1.id, actor_user_id=user2.id, type=notification_type)
            .first()
        )

        assert notification is not None
        assert notification.message == expected_message
        assert notification.target_url == expected_url
        assert notification.is_read is False

        # Clean up for next test
        test_session.delete(notification)
        test_session.commit()


def test_notification_with_missing_actor(test_session):
    """Test notification creation with missing actor user."""
    # Create only one user
    user1 = User(email="user1@test.com", password_hash="hash1", display_name="User One")
    test_session.add(user1)
    test_session.commit()

    # Try to create notification with non-existent actor
    create_notification(user1.id, 999, "post_liked", None)

    # Should not create a notification
    notification = test_session.query(Notification).first()
    assert notification is None


def test_unknown_notification_type(test_session):
    """Test notification creation with unknown type."""
    # Create test users
    user1 = User(email="user1@test.com", password_hash="hash1", display_name="User One")
    user2 = User(email="user2@test.com", password_hash="hash2", display_name="User Two")
    test_session.add_all([user1, user2])
    test_session.commit()

    # Try to create notification with unknown type
    create_notification(user1.id, user2.id, "unknown_type", None)

    # Should not create a notification
    notification = test_session.query(Notification).first()
    assert notification is None
