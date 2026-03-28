"""
Development-specific Django settings.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Use console email backend in development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Disable throttling in development
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}  # noqa: F405

# CORS - allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Additional development apps
INSTALLED_APPS += [  # noqa: F405
    "drf_spectacular",
]

# Simplified logging for development
LOGGING["root"]["level"] = "DEBUG"  # noqa: F405

# Create logs directory
import os
os.makedirs(BASE_DIR / "logs", exist_ok=True)  # noqa: F405
