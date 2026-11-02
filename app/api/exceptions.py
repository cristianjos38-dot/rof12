import uuid

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiDomainError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code, self.message, self.status_code = code, message, status_code


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or str(uuid.uuid4())


async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "request failed"
    return JSONResponse({"code": "HTTP_ERROR", "message": detail, "request_id": request_id(request)}, status_code=exc.status_code)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"code": "VALIDATION_ERROR", "message": "request validation failed", "request_id": request_id(request)}, status_code=422)


async def domain_exception_handler(request: Request, exc: ApiDomainError):
    return JSONResponse({"code": exc.code, "message": exc.message, "request_id": request_id(request)}, status_code=exc.status_code)

