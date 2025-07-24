import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from functools import lru_cache

# Load environment variables from the .env file in the project root
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
