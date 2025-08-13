from sqlalchemy import (
    Column,
    Integer,
    String,
    SmallInteger,
    TIMESTAMP,
    ForeignKey,
    ForeignKeyConstraint,
    Date,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    display_name  = Column(String(100), nullable=False)
    role          = Column(String(20), nullable=False, default="user")
    google_id     = Column(String(255), unique=True, index=True, nullable=True)
    created_at    = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # все действия пользователя
    actions = relationship("UserMovieAction", back_populates="user")


class Movie(Base):
    __tablename__ = "movies"

    id             = Column(Integer, primary_key=True, index=True)
    tmdb_movie_id  = Column(Integer, unique=True, index=True, nullable=False)
    title          = Column(String(255), nullable=False)
    release_date   = Column(Date, nullable=True)
    overview       = Column(Text, nullable=True)
    poster_path    = Column(String(512), nullable=True)
    created_at     = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # все действия, где это фильм
    actions = relationship(
        "UserMovieAction",
        back_populates="movie",
        foreign_keys="[UserMovieAction.tmdb_movie_id]",
        cascade="all, delete-orphan"
    )


class UserMovieAction(Base):
    __tablename__ = "user_movie_actions"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tmdb_movie_id = Column(Integer, nullable=False, index=True)
    action_type   = Column(String(20), nullable=False)  # e.g. "rating", "watchlist"
    rating        = Column(SmallInteger, nullable=True)
    created_at    = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # явная связь через нестандартный FK
    __table_args__ = (
        ForeignKeyConstraint(
            ["tmdb_movie_id"],
            ["movies.tmdb_movie_id"],
            ondelete="CASCADE"
        ),
    )

    # связи
    user  = relationship("User", back_populates="actions")
    movie = relationship(
        "Movie",
        back_populates="actions",
        foreign_keys=[tmdb_movie_id],
        viewonly=True
    )
