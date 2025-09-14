from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from .models import Movie, TvShow, UserMovieAction

class ContentRecommender:
    _cached: "ContentRecommender | None" = None

    @classmethod
    def get_cached(cls, db: Session) -> "ContentRecommender":
        if cls._cached is None:
            cls._cached = cls(db)
        return cls._cached

    @classmethod
    def reset_cache(cls) -> None:
        cls._cached = None

    def __init__(self, db: Session) -> None:
        self._build_matrix(db)

    def _build_matrix(self, db: Session) -> None:
        movies: List[Movie]  = db.query(Movie).all()
        tvs:    List[TvShow] = db.query(TvShow).all()

        rows: List[Tuple[str, int, str]] = []

        for m in movies:
            tmdb_id = int(m.tmdb_movie_id)
            text = f"{m.title or ''}. {m.overview or ''}".strip()
            rows.append(("movie", tmdb_id, text))

        for t in tvs:
            tmdb_id = int(t.tmdb_tv_id)
            title = getattr(t, "name", None) or ""
            text = f"{title}. {t.overview or ''}".strip()
            rows.append(("tv", tmdb_id, text))

        if not rows:
            self.df = pd.DataFrame(columns=["media_type", "tmdb_id", "text"])
            self.mat = None
            self.tmdb2idx: Dict[Tuple[str, int], int] = {}
            return

        self.df = pd.DataFrame(rows, columns=["media_type", "tmdb_id", "text"])

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.9,
        )
        self.mat = self.vectorizer.fit_transform(self.df["text"])
        self.tmdb2idx = {(row.media_type, int(row.tmdb_id)): i
                         for i, row in self.df.iterrows()}

    def _user_profile(self, db: Session, user_id: int):
        if self.mat is None:
            return None

        acts = db.query(UserMovieAction).filter(UserMovieAction.user_id == user_id).all()
        idxs: List[int] = []
        weights: List[float] = []

        for a in acts:
            key_movie = ("movie", a.tmdb_movie_id)
            key_tv    = ("tv", a.tmdb_movie_id)

            i = None
            if key_movie in self.tmdb2idx:
                i = self.tmdb2idx[key_movie]
            elif key_tv in self.tmdb2idx:
                i = self.tmdb2idx[key_tv]

            if i is not None:
                idxs.append(i)
                weights.append(float(a.rating or 1.0))

        if not idxs:
            return None

        sub = self.mat[idxs]
        w = np.asarray(weights, dtype=np.float32)
        s = w.sum()
        if s <= 0:
            w[:] = 1.0 / len(w)
        else:
            w /= s

        prof = sub.multiply(w[:, None]).sum(axis=0)
        prof = np.asarray(prof)
        return prof

    def cb_scores_for_user(self, db: Session, user_id: int) -> Dict[Tuple[str, int], float]:
        if self.mat is None or self.mat.shape[0] == 0:
            return {}

        prof = self._user_profile(db, user_id)
        if prof is None:
            return {}

        sims = linear_kernel(prof, self.mat).ravel()
        out: Dict[Tuple[str, int], float] = {}

        for i in range(self.mat.shape[0]):
            mt = self.df.iloc[i]["media_type"]
            tmdb_id = int(self.df.iloc[i]["tmdb_id"])
            out[(mt, tmdb_id)] = float(sims[i])

        return out
