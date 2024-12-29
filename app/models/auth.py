from sqlalchemy import Column, Integer, String

from app.models.base import Base


class AuthorizedUser(Base):
    __tablename__ = "authorized_users"

    user_id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
