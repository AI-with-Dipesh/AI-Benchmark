from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from aibenchmark.api.schemas.common import ErrorResponse


class APIError(Exception):
    def __init__(self, error: str, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.error = error
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        payload = ErrorResponse(
            error=exc.error,
            detail=exc.detail,
            request_id=getattr(request.state, "request_id", None),
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(payload))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        payload = ErrorResponse(
            error="ValidationError",
            detail=str(exc.errors()),
            request_id=getattr(request.state, "request_id", None),
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=jsonable_encoder(payload))

    @app.exception_handler(ValidationError)
    async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
        payload = ErrorResponse(
            error="ValidationError",
            detail=str(exc.errors()),
            request_id=getattr(request.state, "request_id", None),
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=jsonable_encoder(payload))

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        payload = ErrorResponse(
            error="BadRequest",
            detail=str(exc),
            request_id=getattr(request.state, "request_id", None),
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=jsonable_encoder(payload))

    from aibenchmark.app.config import ConfigError as _ConfigError

    @app.exception_handler(_ConfigError)
    async def config_error_handler(request: Request, exc: _ConfigError):
        payload = ErrorResponse(
            error="BadRequest",
            detail=str(exc),
            request_id=getattr(request.state, "request_id", None),
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=jsonable_encoder(payload))

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        payload = ErrorResponse(
            error="InternalServerError",
            detail=str(exc),
            request_id=getattr(request.state, "request_id", None),
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=jsonable_encoder(payload))
