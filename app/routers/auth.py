from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
import requests

from .. import crud, schemas
from ..database import get_db
from ..utils.security import (
    verify_password,
    hash_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# === Standard registration ===
@router.post(
    "/register",
    response_model=schemas.User,
    status_code=status.HTTP_201_CREATED
)
def register(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = crud.create_user(db, user)
    return new_user


# === Standard login via email/password ===
@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token({"user_id": user.id, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


# === Get the current user via Bearer token ===
@router.get("/me", response_model=schemas.User)
def read_current_user(
    current_user: schemas.User = Depends(get_current_user)
):
    return current_user


# === Google login ===

class GoogleToken(BaseModel):
    token: str


@router.post("/google", response_model=schemas.Token)
def google_auth(
    data: GoogleToken,
    db: Session = Depends(get_db),
):
    # Verify the id_token with Google
    resp = requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"id_token": data.token}
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    info = resp.json()
    google_id = info["sub"]
    email     = info.get("email")
    name      = info.get("name") or info.get("email").split("@")[0]

    # Look up user by google_id or create a new one
    user = crud.get_user_by_google_id(db, google_id)
    if not user:
        user = crud.create_user(db, schemas.UserCreate(
            display_name=name,
            email=email,
            password=None,       # no password for Google signup
            google_id=google_id
        ))

    # Generate our own JWT
    token = create_access_token({"user_id": user.id, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}
