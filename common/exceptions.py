from rest_framework.views import exception_handler as drf_exception_handler
from django.http import Http404


class AppError(Exception):
    code = "APP_ERROR"
    status = 400
    message = "Application error"

    def __init__(self, message=None, *, details=None):
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)


class PermissionDenied(AppError):
    code = "PERMISSION_DENIED"
    status = 403
    message = "You do not have permission"


class ConflictError(AppError):
    code = "CONFLICT"
    status = 409
    message = "Conflict"


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status = 404
    message = "Not found"


def custom_exception_handler(exc, context):
    """
    Unified error format.
    """
    response = drf_exception_handler(exc, context)

    if response is not None:
        return response

    if isinstance(exc, Http404):
        from rest_framework.response import Response
        return Response(
            {"error": {"code": "NOT_FOUND", "message": "Not found", "details": {}}},
            status=404,
        )

    # fallback
    from rest_framework.response import Response
    return Response(
        {"error": {"code": "INTERNAL_ERROR", "message": "Internal server error", "details": {}}},
        status=500,
    )