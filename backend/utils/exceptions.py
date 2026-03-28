"""
Custom exception handling for QualityGate API.
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error response format.

    Response format:
    {
        "error": true,
        "message": "Human-readable error message",
        "code": "ERROR_CODE",
        "details": { ... },   # optional field-level errors
    }
    """
    # Call DRF's default handler first
    response = exception_handler(exc, context)

    if response is None:
        # Handle Django ValidationError
        if isinstance(exc, DjangoValidationError):
            data = {
                "error": True,
                "message": "Validation error",
                "code": "VALIDATION_ERROR",
                "details": exc.message_dict if hasattr(exc, "message_dict") else {"non_field_errors": exc.messages},
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        # Unhandled exception -- log and return generic 500
        logger.exception(
            "Unhandled exception in %s",
            context.get("view", "unknown view"),
            exc_info=exc,
        )
        data = {
            "error": True,
            "message": "An internal server error occurred.",
            "code": "INTERNAL_ERROR",
        }
        return Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Format handled exceptions consistently
    error_data = {
        "error": True,
        "code": _get_error_code(exc),
    }

    if isinstance(exc, ValidationError):
        error_data["message"] = "Validation error"
        error_data["details"] = response.data
    elif isinstance(exc, Http404):
        error_data["message"] = "Resource not found."
    else:
        error_data["message"] = _get_error_message(response.data)

    response.data = error_data
    return response


def _get_error_code(exc):
    """Extract or generate error code from exception."""
    if hasattr(exc, "default_code"):
        return exc.default_code.upper()
    status_code = getattr(exc, "status_code", 500)
    code_map = {
        400: "BAD_REQUEST",
        401: "AUTHENTICATION_FAILED",
        403: "PERMISSION_DENIED",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        429: "THROTTLED",
    }
    return code_map.get(status_code, "ERROR")


def _get_error_message(data):
    """Extract human-readable message from DRF error data."""
    if isinstance(data, dict):
        detail = data.get("detail", "")
        if detail:
            return str(detail)
        # Flatten field errors
        messages = []
        for field, errors in data.items():
            if isinstance(errors, list):
                messages.extend([str(e) for e in errors])
            else:
                messages.append(str(errors))
        return "; ".join(messages) if messages else "An error occurred."
    if isinstance(data, list):
        return "; ".join([str(item) for item in data])
    return str(data)


class ConflictError(APIException):
    """409 Conflict error."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This action conflicts with the current state of the resource."
    default_code = "CONFLICT"


class BusinessRuleViolation(APIException):
    """422 Unprocessable Entity for business rule violations."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "The request violates a business rule."
    default_code = "BUSINESS_RULE_VIOLATION"
