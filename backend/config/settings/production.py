"""
Production-specific Django settings.
"""

from .base import *  # noqa: F401, F403

DEBUG = False

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"

# Ensure secret key is set
if SECRET_KEY == "insecure-dev-key-change-in-production":  # noqa: F405
    raise ValueError("DJANGO_SECRET_KEY must be set in production!")

# Production logging
LOGGING["handlers"]["file"] = {  # noqa: F405
    "class": "logging.handlers.RotatingFileHandler",
    "filename": BASE_DIR / "logs" / "qualitygate.log",  # noqa: F405
    "maxBytes": 10 * 1024 * 1024,  # 10 MB
    "backupCount": 5,
    "formatter": "verbose",
}

LOGGING["root"]["level"] = "WARNING"  # noqa: F405

# Create logs directory
import os
os.makedirs(BASE_DIR / "logs", exist_ok=True)  # noqa: F405

# Cache
CACHES["default"]["OPTIONS"] = {  # noqa: F405
    "CLIENT_CLASS": "django.core.cache.backends.redis.RedisCache",
}

# Celery production settings
CELERY_TASK_ALWAYS_EAGER = False
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
