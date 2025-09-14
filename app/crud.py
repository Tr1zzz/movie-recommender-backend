from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from . import models, schemas
from .utils.crypto import hash_password

# ─── User operations ──────────────────────────────────────────────────────────

def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_google_id(db: Session, google_id: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.google_id == google_id).first()

def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
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

def create_or_update_user_action(
    db: Session,
    user_id: int,
    action: schemas.UserActionCreate,
) -> Tuple[models.UserMovieAction, bool]:
    existing = (
        db.query(models.UserMovieAction)
        .filter_by(
            user_id=user_id,
            tmdb_movie_id=action.tmdb_movie_id,
            action_type=action.action_type,
        )
        .first()
    )

    if existing:
        if action.action_type == "rating":
            existing.rating = action.rating
        db.commit()
        db.refresh(existing)
        return existing, False

    db_act = models.UserMovieAction(
        user_id=user_id,
        tmdb_movie_id=action.tmdb_movie_id,
        action_type=action.action_type,
        rating=action.rating,
    )
    db.add(db_act)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return create_or_update_user_action(db, user_id, action)
    db.refresh(db_act)
    return db_act, True


def create_user_action(
    db: Session,
    user_id: int,
    action: schemas.UserActionCreate,
) -> models.UserMovieAction:
    obj, _ = create_or_update_user_action(db, user_id, action)
    return obj

def get_user_actions(
    db: Session,
    user_id: int,
    action_type: Optional[str] = None,
) -> List[models.UserMovieAction]:
    q = db.query(models.UserMovieAction).filter_by(user_id=user_id)
    if action_type:
        q = q.filter_by(action_type=action_type)
    return q.all()
