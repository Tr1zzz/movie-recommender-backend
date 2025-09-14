from __future__ import annotations
from functools import lru_cache
from typing import List, Dict
from sqlalchemy.orm import Session
from .cf import ItemItemCF
from .content import ContentBased
from ..models import UserMovieAction

import os
from pathlib import Path
import json


CACHE_DIR = Path(os.getenv("RECOMMENDER_CACHE_DIR", ".cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ALPHA = 0.6  

class HybridRecommender:
    def __init__(self, db: Session):
        self.cf = ItemItemCF(db)
        self.cb = ContentBased(db)

    def recommend_for_user(self, db: Session, user_id: int, n: int = 10) -> List[int]:
        cf = self.cf.score_for_user(user_id)
        cb = self.cb.score_for_user(db, user_id)

        seen = {
            t for (t,) in db.query(UserMovieAction.tmdb_movie_id)
                            .filter(UserMovieAction.user_id == user_id).all()
        }

        ids = set(cf) | set(cb)
        scores: Dict[int, float] = {}
        for m in ids:
            if m in seen:
                continue
            scores[m] = ALPHA * cf.get(m, 0.0) + (1 - ALPHA) * cb.get(m, 0.0)

        return [mid for mid, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:n]]

META_PATH = CACHE_DIR / "recommender_meta.json"

@lru_cache(maxsize=1)
def _meta_key() -> str:
    if META_PATH.exists():
        return META_PATH.read_text(encoding="utf-8")
    txt = '{"version":1}'
    META_PATH.write_text(txt, encoding="utf-8")
    return txt

@lru_cache(maxsize=1)
def get_recommender(db: Session, _key: str) -> HybridRecommender:
    return HybridRecommender(db)

def reset_recommender_cache():
    get_recommender.cache_clear()
    try:
        if META_PATH.exists():
            obj = json.loads(META_PATH.read_text(encoding="utf-8"))
            obj["version"] = int(obj.get("version", 1)) + 1
        else:
            obj = {"version": 1}
    except Exception:
        obj = {"version": 1}
    META_PATH.write_text(json.dumps(obj), encoding="utf-8")
    _meta_key.cache_clear()
