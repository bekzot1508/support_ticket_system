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