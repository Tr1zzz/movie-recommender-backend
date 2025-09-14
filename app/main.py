from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base, SessionLocal
from .routers import actions, recommendations, auth   # ← добавили auth
from .recommenders.hybrid import get_recommender, _meta_key

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Movie Recommender API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def warmup():
    with SessionLocal() as db:
        get_recommender(db, _meta_key())

app.include_router(auth.router)
app.include_router(actions.router)
app.include_router(recommendations.router)
