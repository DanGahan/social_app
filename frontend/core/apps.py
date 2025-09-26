"""Django app configuration for core module."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration class for the core Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
