from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr

# ───── User schemas ──────────────────────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    display_name: str

class UserCreate(UserBase):
    password: Optional[str] = None
    google_id: Optional[str] = None
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

# ───── Recommendation schemas ────────────────────────────────────────────────

class RecommendationItem(BaseModel):
    tmdb_id: int
    media_type: Literal["movie", "tv"]
    title: Optional[str] = None
    poster_path: Optional[str] = None
    score: Optional[float] = None
