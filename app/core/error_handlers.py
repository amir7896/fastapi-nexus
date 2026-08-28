from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

_LOCATION_KEYS = ("body", "query", "path", "header", "cookie")


def _field_name(error: dict) -> str:
    parts = [str(part) for part in error.get("loc", []) if part not in _LOCATION_KEYS]
    return parts[-1] if parts else "field"


def _friendly_message(error: dict) -> str:
    field = _field_name(error)
    error_type = error.get("type", "")
    ctx = error.get("ctx") or {}
    original = error.get("msg", "Invalid value")
    value = error.get("input")

    if error_type in ("json_invalid", "json_type"):
        return "Invalid JSON in request body"

    if "email" in error_type or (
        error_type == "value_error" and "email" in original.lower()
    ):
        return f"{field} must be a valid email address"

    if value is None and error_type in (
        "string_type",
        "int_type",
        "float_type",
        "bool_type",
        "list_type",
        "dict_type",
    ):
        return f"{field} cannot be null"

    messages = {
        "missing": f"{field} is required",
        "none_required": f"{field} cannot be null",
        "string_type": f"{field} must be a string",
        "string_too_short": f"{field} must be at least {ctx.get('min_length')} characters",
        "string_too_long": f"{field} must be at most {ctx.get('max_length')} characters",
        "string_pattern_mismatch": f"{field} format is invalid",
        "int_type": f"{field} must be an integer",
        "int_parsing": f"{field} must be an integer",
        "int_from_float": f"{field} must be an integer",
        "float_type": f"{field} must be a number",
        "float_parsing": f"{field} must be a number",
        "bool_type": f"{field} must be a boolean",
        "bool_parsing": f"{field} must be a boolean",
        "greater_than_equal": f"{field} must be greater than or equal to {ctx.get('ge')}",
        "greater_than": f"{field} must be greater than {ctx.get('gt')}",
        "less_than_equal": f"{field} must be less than or equal to {ctx.get('le')}",
        "less_than": f"{field} must be less than {ctx.get('lt')}",
        "multiple_of": f"{field} must be a multiple of {ctx.get('multiple_of')}",
        "finite_number": f"{field} must be a finite number",
        "list_type": f"{field} must be a list",
        "tuple_type": f"{field} must be a list",
        "set_type": f"{field} must be a list",
        "dict_type": f"{field} must be an object",
        "iterable_type": f"{field} must be a list",
        "too_short": f"{field} must have at least {ctx.get('min_length')} items",
        "too_long": f"{field} must have at most {ctx.get('max_length')} items",
        "extra_forbidden": f"{field} is not allowed",
        "literal_error": f"{field} has an invalid value",
        "enum": f"{field} has an invalid value",
        "uuid_parsing": f"{field} must be a valid UUID",
        "uuid_type": f"{field} must be a valid UUID",
        "date_parsing": f"{field} must be a valid date",
        "date_from_datetime_parsing": f"{field} must be a valid date",
        "date_type": f"{field} must be a valid date",
        "datetime_parsing": f"{field} must be a valid datetime",
        "datetime_from_date_parsing": f"{field} must be a valid datetime",
        "datetime_type": f"{field} must be a valid datetime",
        "time_parsing": f"{field} must be a valid time",
        "time_type": f"{field} must be a valid time",
        "url_parsing": f"{field} must be a valid URL",
        "url_scheme": f"{field} must be a valid URL",
        "url_type": f"{field} must be a valid URL",
        "bytes_type": f"{field} must be valid bytes",
        "decimal_parsing": f"{field} must be a valid decimal",
        "decimal_type": f"{field} must be a valid decimal",
        "frozen_field": f"{field} cannot be modified",
        "value_error": original,
        "assertion_error": original,
    }

    return messages.get(error_type, original)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = []
    for error in exc.errors():
        formatted = dict(error)
        formatted["msg"] = _friendly_message(error)
        errors.append(formatted)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": jsonable_encoder(errors)},
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
