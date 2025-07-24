from sqlalchemy import (
    Column,
    Integer,
    String,
    SmallInteger,
    TIMESTAMP,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship

from .database import Base

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)   # now nullable=True to allow social login users without passwords
    display_name  = Column(String(100), nullable=False)
    role          = Column(String(20), nullable=False, default="user")
    google_id     = Column(String(255), unique=True, index=True, nullable=True)
    created_at    = Column(TIMESTAMP(timezone=True), server_default=func.now())

    actions = relationship("UserMovieAction", back_populates="user")

class UserMovieAction(Base):
    __tablename__ = "user_movie_actions"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tmdb_movie_id = Column(Integer, nullable=False)
    action_type   = Column(String(20), nullable=False)
    rating        = Column(SmallInteger)
    created_at    = Column(TIMESTAMP(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="actions")
