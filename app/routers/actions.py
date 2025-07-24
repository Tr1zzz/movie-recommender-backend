from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import crud, schemas, models
from ..database import get_db
from ..config import settings

router = APIRouter(
    prefix="/user",
    tags=["actions"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def decode_access_token(token: str) -> schemas.TokenData:
    """
    Decode a JWT and return a TokenData containing user_id and role.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("user_id")
        role: str = payload.get("role")
        if user_id is None or role is None:
            raise JWTError()
        return schemas.TokenData(user_id=user_id, role=role)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(token: str = Depends(oauth2_scheme)) -> schemas.TokenData:
    """
    Dependency: parses the token and returns TokenData.
    """
    return decode_access_token(token)


@router.post(
    "/actions",
    response_model=schemas.UserAction,
    status_code=status.HTTP_201_CREATED,
)
def add_action(
    action: schemas.UserActionCreate,
    token_data: schemas.TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a user action (like, watchlist, rating).
    """
    # verify that the user exists
    user = db.query(models.User).get(token_data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # create the action record
    db_act = crud.create_user_action(db, token_data.user_id, action)
    return db_act


@router.get(
    "/actions",
    response_model=List[schemas.UserAction],
    status_code=status.HTTP_200_OK,
)
def list_actions(
    action_type: Optional[str] = None,
    token_data: schemas.TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve all actions of the current user,
    optionally filtering by action_type.
    """
    return crud.get_user_actions(db, token_data.user_id, action_type)
