"""Database models for the social media application."""

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """User model representing registered users in the system."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=True)  # New field
    profile_picture_url = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=func.now())

    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    # Relationships for connections
    connections_as_user1 = relationship(
        "Connection",
        foreign_keys="[Connection.user_id1]",
        back_populates="user1",
    )
    connections_as_user2 = relationship(
        "Connection",
        foreign_keys="[Connection.user_id2]",
        back_populates="user2",
    )
    # Relationships for connection requests
    sent_requests = relationship(
        "ConnectionRequest",
        foreign_keys="[ConnectionRequest.from_user_id]",
        back_populates="from_user",
    )
    received_requests = relationship(
        "ConnectionRequest",
        foreign_keys="[ConnectionRequest.to_user_id]",
        back_populates="to_user",
    )
    likes = relationship("Like", cascade="all, delete-orphan")
    comments = relationship("Comment", cascade="all, delete-orphan")


class Post(Base):
    """Post model representing user posts/photos in the system."""

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_url = Column(Text, nullable=False)
    caption = Column(Text)
    created_at = Column(TIMESTAMP, default=func.now())

    user = relationship("User", back_populates="posts")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")
    comments = relationship(
        "Comment", back_populates="post", cascade="all, delete-orphan"
    )


class Connection(Base):
    """Connection model representing user follow relationships."""

    __tablename__ = "connections"

    id = Column(Integer, primary_key=True)
    user_id1 = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_id2 = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())

    user1 = relationship("User", foreign_keys="[Connection.user_id1]")
    user2 = relationship("User", foreign_keys="[Connection.user_id2]")

    __table_args__ = (UniqueConstraint("user_id1", "user_id2", name="_user1_user2_uc"),)


class ConnectionRequest(Base):
    """ConnectionRequest model representing pending follow requests."""

    __tablename__ = "connection_requests"

    id = Column(Integer, primary_key=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(
        String(50), default="pending", nullable=False
    )  # e.g., 'pending', 'accepted', 'rejected'
    created_at = Column(TIMESTAMP, default=func.now())

    from_user = relationship("User", foreign_keys="[ConnectionRequest.from_user_id]")
    to_user = relationship("User", foreign_keys="[ConnectionRequest.to_user_id]")

    __table_args__ = (
        UniqueConstraint("from_user_id", "to_user_id", name="_from_to_user_uc"),
    )


class Like(Base):
    """Like model representing user likes on posts."""

    __tablename__ = "likes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())

    user = relationship("User", overlaps="likes")
    post = relationship("Post", back_populates="likes")

    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="_user_post_like_uc"),
    )


class Comment(Base):
    """Comment model representing comments on posts."""

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())

    user = relationship("User", overlaps="comments")
    post = relationship("Post", back_populates="comments")


class Notification(Base):
    """Notification model representing user notifications."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # recipient
    actor_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False
    )  # who triggered
    type = Column(
        String(50), nullable=False
    )  # 'post_liked', 'post_commented', 'connection_request', 'connection_accepted'
    post_id = Column(
        Integer, ForeignKey("posts.id"), nullable=True
    )  # for post-related notifications
    message = Column(Text, nullable=False)  # pre-formatted message
    target_url = Column(String(255), nullable=False)  # navigation URL
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    actor_user = relationship("User", foreign_keys=[actor_user_id])
    post = relationship("Post")
