import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Connection, ConnectionRequest, Post, User

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)


@pytest.fixture(scope="module")
def setup_database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_user_creation(setup_database):
    session = setup_database
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        display_name="Test User",
    )
    session.add(user)
    session.commit()
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.display_name == "Test User"


def test_post_creation(setup_database):
    session = setup_database
    user = User(email="post_user@example.com", password_hash="hashed_password")
    session.add(user)
    session.commit()

    post = Post(
        user_id=user.id,
        image_url="http://example.com/image.jpg",
        caption="Test Post",
    )
    session.add(post)
    session.commit()

    assert post.id is not None
    assert post.user_id == user.id
    assert post.caption == "Test Post"
    assert post.user.email == "post_user@example.com"


def test_connection_creation(setup_database):
    session = setup_database
    user1 = User(email="user1@example.com", password_hash="hashed_password1")
    user2 = User(email="user2@example.com", password_hash="hashed_password2")
    session.add_all([user1, user2])
    session.commit()

    connection = Connection(user_id1=user1.id, user_id2=user2.id)
    session.add(connection)
    session.commit()

    assert connection.id is not None
    assert connection.user_id1 == user1.id
    assert connection.user_id2 == user2.id


def test_connection_request_creation(setup_database):
    session = setup_database
    from_user = User(
        email="from@example.com", password_hash="hashed_password_from"
    )
    to_user = User(email="to@example.com", password_hash="hashed_password_to")
    session.add_all([from_user, to_user])
    session.commit()

    request = ConnectionRequest(
        from_user_id=from_user.id, to_user_id=to_user.id, status="pending"
    )
    session.add(request)
    session.commit()

    assert request.id is not None
    assert request.from_user_id == from_user.id
    assert request.to_user_id == to_user.id
    assert request.status == "pending"
    assert request.from_user.email == "from@example.com"
    assert request.to_user.email == "to@example.com"
