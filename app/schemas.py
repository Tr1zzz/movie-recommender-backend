from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

# ───── User schemas ──────────────────────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    display_name: str

class UserCreate(UserBase):
    # Password is now optional (for Google login)
    password: Optional[str] = None
    # Pass google_id when logging in via Google
    google_id: Optional[str] = None
    # Role will always be set to "user" on the backend,
    # but kept optional here if you ever need to override
    role: Optional[str] = None

class User(UserBase):
    id: int
    role: str
    created_at: datetime
    google_id: Optional[str] = None

    model_config = {
        "from_attributes": True,  # Pydantic v2: read values from ORM attributes
    }

# ───── Token schemas ─────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None

# ───── User–Movie Action schemas ─────────────────────────────────────────────

class UserActionBase(BaseModel):
    tmdb_movie_id: int
    action_type: str      # e.g., "like", "watchlist", "rating"
    rating: Optional[int] = None

class UserActionCreate(UserActionBase):
    pass

class UserAction(UserActionBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }
