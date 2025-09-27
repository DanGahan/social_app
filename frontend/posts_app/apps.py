"""Django app configuration for posts_app module."""

from django.apps import AppConfig


class PostsAppConfig(AppConfig):
    """Configuration class for the posts_app Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "posts_app"
