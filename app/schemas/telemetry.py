from pydantic import BaseModel


class TelemetryPayload(BaseModel):
    event: str
    details: dict
