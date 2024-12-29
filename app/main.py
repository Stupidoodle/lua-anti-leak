from fastapi import FastAPI

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.script import router as script_router
from app.api.v1.endpoints.telemetry import router as telemetry_router

app = FastAPI()

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(script_router, prefix="/api/v1/script", tags=["script"])
app.include_router(telemetry_router, prefix="/api/v1/telemetry", tags=["telemetry"])
