from django.core.exceptions import RequestDataTooBig
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


class PlanError(Exception):
    def __init__(self, message, code="invalid_input", status=400):
        super().__init__(message)
        self.code = code
        self.status = status


def error_body(code, message, **extra):
    return {"error": {"code": code, "message": message, **extra}}


def flatten(detail, loc=()):
    if isinstance(detail, dict):
        out = []
        for key, value in detail.items():
            out += flatten(value, loc + (key,))
        return out
    if isinstance(detail, list):
        out = []
        for value in detail:
            out += flatten(value, loc)
        return out
    return [{"loc": list(loc) or ["non_field_errors"], "type": getattr(detail, "code", "invalid"), "msg": str(detail)}]


def handle_api_error(exc, context):
    if isinstance(exc, PlanError):
        return Response(error_body(exc.code, str(exc)), status=exc.status)
    if isinstance(exc, RequestDataTooBig):
        return Response(error_body("request_too_large", "Request body is too large."), status=413)
    response = exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, (ValidationError, ParseError)):
        response.data = error_body("invalid_input", "Request validation failed.", details=flatten(exc.detail))
    else:
        response.data = error_body(getattr(exc, "default_code", "request_error"), str(exc.detail))
    return response
