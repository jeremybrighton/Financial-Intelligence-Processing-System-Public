"""
FRC System — Custom Exceptions and Global Error Handlers
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class FRCException(Exception):
    def __init__(self, message: str, status_code: int = 500, detail: dict = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)

class NotFoundError(FRCException):
    def __init__(self, resource: str, identifier: str = ""):
        msg = f"{resource} not found" if not identifier else f"{resource} '{identifier}' not found"
        super().__init__(msg, status_code=404)

class ConflictError(FRCException):
    def __init__(self, message: str):
        super().__init__(message, status_code=409)

class IntakeError(FRCException):
    def __init__(self, message: str, detail: dict = None):
        super().__init__(message, status_code=422, detail=detail or {})


def error_response(message: str, detail=None, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": False, "error": message, "detail": detail or {}})


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(FRCException)
    async def frc_handler(request: Request, exc: FRCException):
        return error_response(exc.message, exc.detail, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"success": False, "error": "Validation failed", "detail": exc.errors()})

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return error_response(f"Not found: {request.method} {request.url.path}", status_code=404)

    @app.exception_handler(500)
    async def server_error_handler(request: Request, exc):
        return error_response("Internal server error", status_code=500)
