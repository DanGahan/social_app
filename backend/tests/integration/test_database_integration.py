"""
Backend-Database Integration Tests

Tests real database operations with actual PostgreSQL container.
Covers CRUD operations, transactions, and connection handling.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from app import app
from models import Base, Comment, Connection, Like, Post, User


@pytest.fixture(scope="module")
def postgres_container():
    """Start PostgreSQL container for integration tests."""
    with PostgresContainer("postgres:13") as postgres:
        yield postgres


@pytest.fixture(scope="module")
def test_engine(postgres_container):
    """Create SQLAlchemy engine connected to test database."""
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
    # Store original session
    from app import session as original_session

    # Create new session for test database
    Session = sessionmaker(bind=test_engine)
    test_session = Session()

    # Replace app's session with test session
    app.config["TESTING"] = True
    import app as app_module

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
        user1 = User(email="user1@example.com", password_hash="hash1")
        user2 = User(email="user2@example.com", password_hash="hash2")
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
