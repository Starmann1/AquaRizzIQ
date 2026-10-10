from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, Optional

class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: Optional[str] = None
    instance: Optional[str] = None
    extensions: Dict[str, Any] = {}

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
    problem = ProblemDetails(
        type="about:blank",
        title=exc.title,
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url),
        extensions=exc.extensions
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_unset=True),
        headers={"Content-Type": "application/problem+json"}
    )
