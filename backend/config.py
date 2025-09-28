"""Configuration module for the social media application."""

import os
import secrets
import warnings


class Config:
    """Application configuration class containing database and security settings."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        # Generate a secure random key for development, but warn about it
        SECRET_KEY = secrets.token_hex(32)
        warnings.warn(
            "No SECRET_KEY environment variable set. Generated a random key for this session. "
            "For production, set SECRET_KEY environment variable to a secure, persistent value.",
            UserWarning,
            stacklevel=2,
        )

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://user:password@database:5432/social_db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
