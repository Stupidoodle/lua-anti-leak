from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, Integer, String

from app.models.base import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    event = Column(String, nullable=False)
    data = Column(JSONB, nullable=True)
