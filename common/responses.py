from rest_framework.response import Response

def error_response(exc):
    return Response(
        {
            "error": {
                "code": getattr(exc, "code", "APP_ERROR"),
                "message": getattr(exc, "message", str(exc)),
                "details": getattr(exc, "details", {}),
            }
        },
        status=getattr(exc, "status", 400),
    )