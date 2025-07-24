from typing import Optional, List
from sqlalchemy.orm import Session

from . import models, schemas
from .utils.security import hash_password


# ─── User operations ──────────────────────────────────────────────────────────

def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_google_id(db: Session, google_id: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.google_id == google_id).first()

def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    """
    Create a new user.
    - If user_in.password is provided, hash it.
    - If user_in.google_id is provided, save it.
    The role is always set to 'user', even if user_in.role is provided.
    """
    pwd_hash = hash_password(user_in.password) if user_in.password else None

    db_user = models.User(
        email=user_in.email,
        password_hash=pwd_hash,
        display_name=user_in.display_name,
        role="user",
        google_id=user_in.google_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# ─── UserMovieAction operations ──────────────────────────────────────────────

def create_user_action(
    db: Session,
    user_id: int,
    action: schemas.UserActionCreate,
) -> models.UserMovieAction:
    db_act = models.UserMovieAction(
        user_id=user_id,
        tmdb_movie_id=action.tmdb_movie_id,
        action_type=action.action_type,
        rating=action.rating,
    )
    db.add(db_act)
    db.commit()
    db.refresh(db_act)
    return db_act

def get_user_actions(
    db: Session,
    user_id: int,
    action_type: Optional[str] = None,
) -> List[models.UserMovieAction]:
    """
    Retrieve all movie actions for a user, optionally filtering by action_type.
    """
    q = db.query(models.UserMovieAction).filter_by(user_id=user_id)
    if action_type:
        q = q.filter_by(action_type=action_type)
    return q.all()
