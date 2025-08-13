from __future__ import annotations
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from typing import Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from ..models import Movie, UserMovieAction

class ContentBased:
    def __init__(self, db: Session):
        self._build(db)

    def _build(self, db: Session):
        movies = db.query(Movie).all()
        self.df = pd.DataFrame({
            "tmdb_id": [m.tmdb_movie_id for m in movies],
            "title":   [m.title for m in movies],
            "text":    [f"{m.title or ''}. {m.overview or ''}" for m in movies],
        })
        if self.df.empty:
            self.mat = None; self.tmdb2idx = {}; return
        vect = TfidfVectorizer(stop_words="english", ngram_range=(1,2), min_df=2, max_df=0.9)
        self.mat = vect.fit_transform(self.df["text"])
        self.tmdb2idx = {int(t): i for i, t in enumerate(self.df["tmdb_id"])}

    def _user_profile(self, db: Session, user_id: int):
        acts = db.query(UserMovieAction).filter(UserMovieAction.user_id == user_id).all()
        idxs, weights = [], []
        for a in acts:
            i = self.tmdb2idx.get(a.tmdb_movie_id)
            if i is not None:
                idxs.append(i); weights.append(float(a.rating or 1.0))
        if not idxs: return None
        return np.average(self.mat[idxs], axis=0, weights=weights)

    def score_for_user(self, db: Session, user_id: int) -> Dict[int, float]:
        if not self.tmdb2idx or self.mat is None: return {}
        prof = self._user_profile(db, user_id)
        if prof is None: return {}
        sims = linear_kernel(prof, self.mat).ravel()
        return {int(self.df.loc[i,"tmdb_id"]): float(sims[i]) for i in range(len(sims))}
