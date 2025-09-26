"""Configuration module for the social media application."""

import os


class Config:
    """Application configuration class containing database and security settings."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "a_very_secret_key")  # Added for JWT
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://user:password@database:5432/social_db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
