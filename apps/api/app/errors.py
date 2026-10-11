from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Any, Optional


def _problem_response(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: Optional[str] = None,
    extensions: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status_code,
        "instance": str(request.url),
        "request_id": getattr(request.state, "request_id", None),
    }
    if detail is not None:
        body["detail"] = detail
    if extensions:
        body.update(extensions)
    response_headers = {"Content-Type": "application/problem+json", **(headers or {})}
    return JSONResponse(
        status_code=status_code,
        content=body,
        headers=response_headers,
    )

class AppError(Exception):
    def __init__(self, status_code: int, title: str, detail: Optional[str] = None, **kwargs: Any):
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.extensions = kwargs
        super().__init__(self.detail or self.title)

class NotFoundError(AppError):
    def __init__(self, detail: str = "Resource not found", **kwargs: Any):
        super().__init__(404, "Not Found", detail, **kwargs)

class ConflictError(AppError):
    def __init__(self, detail: str = "Resource conflict", **kwargs: Any):
        super().__init__(409, "Conflict", detail, **kwargs)

class ValidationError(AppError):
    def __init__(self, detail: str = "Validation failed", **kwargs: Any):
        super().__init__(422, "Unprocessable Entity", detail, **kwargs)

class AuthenticationError(AppError):
    def __init__(self, detail: str = "Authentication failed", **kwargs: Any):
        super().__init__(401, "Unauthorized", detail, **kwargs)

class AuthorizationError(AppError):
    def __init__(self, detail: str = "Authorization failed", **kwargs: Any):
        super().__init__(403, "Forbidden", detail, **kwargs)

class StaleDataError(AppError):
    def __init__(self, detail: str = "Data is stale", **kwargs: Any):
        super().__init__(412, "Precondition Failed", detail, **kwargs)

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _problem_response(
        request,
        status_code=exc.status_code,
        title=exc.title,
        detail=exc.detail,
        extensions=exc.extensions,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
    title = {
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        409: "Conflict",
        422: "Unprocessable Entity",
        503: "Service Unavailable",
    }.get(exc.status_code, "HTTP Error")
    return _problem_response(
        request,
        status_code=exc.status_code,
        title=title,
        detail=detail,
        headers=exc.headers,
    )


async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Do not echo submitted values: validation inputs can contain credentials or personal data.
    errors = [
        {"location": list(error.get("loc", ())), "message": error.get("msg", "Invalid value"), "code": error.get("type")}
        for error in exc.errors()
    ]
    return _problem_response(
        request,
        status_code=422,
        title="Request validation failed",
        detail="One or more request fields are invalid.",
        extensions={"errors": errors},
    )
