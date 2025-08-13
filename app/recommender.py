from __future__ import annotations
from typing import Dict, List
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from .models import Movie, UserMovieAction

class ContentRecommender:
    """
    Контентный рекомендатель: TF-IDF по title+overview.
    Профиль пользователя — взвешенная (по rating) сумма TF-IDF векторов просмотренных фильмов.
    """

    _cached: "ContentRecommender | None" = None

    @classmethod
    def get_cached(cls, db: Session) -> "ContentRecommender":
        if cls._cached is None:
            cls._cached = cls(db)
        return cls._cached

    @classmethod
    def reset_cache(cls) -> None:
        cls._cached = None

    # ---------------- internal ----------------
    def __init__(self, db: Session) -> None:
        self._build_matrix(db)

    def _build_matrix(self, db: Session) -> None:
        movies = db.query(Movie).all()
        self.df = pd.DataFrame({
            "tmdb_id": [m.tmdb_movie_id for m in movies],
            "text":    [f"{m.title or ''}. {m.overview or ''}" for m in movies],
        })
        if self.df.empty:
            self.mat = None
            self.tmdb2idx = {}
            return

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.9,
        )
        # scipy.sparse CSR matrix (n_movies x n_features)
        self.mat = self.vectorizer.fit_transform(self.df["text"])
        self.tmdb2idx = {int(t): i for i, t in enumerate(self.df["tmdb_id"])}

    def _user_profile(self, db: Session, user_id: int):
        """Взвешенный (по rating) профиль пользователя как 1×F dense-вектор."""
        if self.mat is None:
            return None

        acts = db.query(UserMovieAction).filter(UserMovieAction.user_id == user_id).all()
        idxs: List[int] = []
        weights: List[float] = []
        for a in acts:
            i = self.tmdb2idx.get(a.tmdb_movie_id)
            if i is not None:
                idxs.append(i)
                weights.append(float(a.rating or 1.0))

        if not idxs:
            return None

        sub = self.mat[idxs]  # k × F sparse
        w = np.asarray(weights, dtype=np.float32)
        s = w.sum()
        if s <= 0:
            w[:] = 1.0 / len(w)
        else:
            w /= s

        prof = sub.multiply(w[:, None]).sum(axis=0)  # -> numpy.matrix (1 × F)
        prof = np.asarray(prof)                      # -> ndarray (1, F)
        return prof

    def cb_scores_for_user(self, db: Session, user_id: int) -> Dict[int, float]:
        """Словарь {tmdb_id: score} по косинусной близости профиля к каждому фильму."""
        if not getattr(self, "tmdb2idx", None) or self.mat is None or self.mat.shape[0] == 0:
            return {}
        prof = self._user_profile(db, user_id)
        if prof is None:
            return {}
        sims = linear_kernel(prof, self.mat).ravel()  # (n_movies,)
        return {int(self.df.loc[i, "tmdb_id"]): float(sims[i]) for i in range(self.mat.shape[0])}
