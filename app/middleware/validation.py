import json
import re
import structlog
from fastapi import Request, HTTPException

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class PayloadTooLarge(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=413, detail="Request payload too large")


class InvalidContentType(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=415, detail="Unsupported media type")


class RequestValidator:
    def __init__(self) -> None:
        self.max_content_length = settings.MAX_CONTENT_LENGTH
        self.allowed_content_types = [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
        ]
        self.logger = logger.bind(component="request_validator")

    async def _validate_content_type(self, request: Request) -> None:
        """Validate the Content-Length header"""
        content_length = request.headers.get("content-length")

        if content_length and int(content_length) > self.max_content_length:
            self.logger.warning(
                "payload_too_large",
                content_length=content_length,
                max_size=self.max_content_length,
                path=request.url.path,
            )
            raise PayloadTooLarge()

    async def _validate_content_length(self, request: Request) -> None:
        """Validate the Content-Length header"""
        content_length = request.headers.get("content-length")

        if content_length and int(content_length) > self.max_content_length:
            self.logger.warning(
                "payload_too_large",
                content_length=content_length,
                max_size=self.max_content_length,
                path=request.url.path,
            )
            raise PayloadTooLarge()

    @staticmethod
    async def _validate_json_depth(data: dict, max_depth: int = 5) -> None:
        """Validate JSON object depth to prevent stack overflow attacks"""

        def check_depth(obj: any, current_depth=1) -> bool:
            if current_depth > max_depth:
                return False

            if isinstance(obj, (dict, list)):
                if not obj:
                    return True

                if isinstance(obj, dict):
                    return all(check_depth(v, current_depth + 1) for v in obj.values())

                return all(check_depth(v, current_depth + 1) for v in obj)

            return True

        if not check_depth(data):
            raise HTTPException(status_code=400, detail="JSON structure too deep")

    async def validate_request(self, request: Request) -> None:
        """Validate incoming request"""
        try:
            if request.url.path == "/health":
                return

            await self._validate_content_type(request)
            await self._validate_content_length(request)

            if "application/json" in request.headers.get("content-type", "").lower():
                data = await request.json()
                await self._validate_json_depth(data)

        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        except Exception as e:
            self.logger.error(
                "request_validation_error", error=str(e), path=request.url.path
            )
            raise


async def validation_middleware(request: Request, call_next: any) -> any:
    """Middleware to validate incoming requests"""
    validator = RequestValidator()
    await validator.validate_request(request)
    response = await call_next(request)
    return response
