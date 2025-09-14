from __future__ import annotations
from typing import Dict, Tuple, List
import numpy as np
from scipy import sparse
from sklearn.preprocessing import normalize
from sqlalchemy.orm import Session

from .models import UserMovieAction, Movie, TvShow


class CFRecommender:
    """Item-based CF. Item key: ('movie'|'tv', tmdb_id)."""

    _cached: "CFRecommender | None" = None

    @classmethod
    def get_cached(cls, db: Session) -> "CFRecommender":
        if cls._cached is None:
            cls._cached = cls(db)
        return cls._cached

    @classmethod
    def reset_cache(cls) -> None:
        cls._cached = None

    def __init__(self, db: Session) -> None:
        self._build(db)

    # ────────────────────────────────────────────────────────────────────
    def _build(self, db: Session) -> None:
        actions: List[UserMovieAction] = db.query(UserMovieAction).all()

        movie_ids = [m[0] for m in db.query(Movie.tmdb_movie_id).all()]
        tv_ids    = [t[0] for t in db.query(TvShow.tmdb_tv_id).all()]

        items: List[Tuple[str, int]] = [("movie", int(x)) for x in set(movie_ids)] + \
                                       [("tv",    int(x)) for x in set(tv_ids)]
        items = sorted(items)

        users = sorted({a.user_id for a in actions})

        self.user2idx = {u: i for i, u in enumerate(users)}
        self.item2idx = {key: i for i, key in enumerate(items)}
        self.idx2item = {i: key for key, i in self.item2idx.items()}

        if not users or not items:
            self.UI = sparse.csr_matrix((0, 0), dtype=np.float32)
            self.item_sim = sparse.csr_matrix((0, 0), dtype=np.float32)
            return

        rows, cols, data = [], [], []

        for a in actions:
            key_movie = ("movie", a.tmdb_movie_id)
            key_tv    = ("tv", a.tmdb_movie_id)

            key = key_movie if key_movie in self.item2idx else \
                  key_tv    if key_tv    in self.item2idx else None
            if key is None:
                continue

            rows.append(self.user2idx[a.user_id])
            cols.append(self.item2idx[key])
            data.append(float(a.rating or 1.0))

        UI = sparse.csr_matrix((data, (rows, cols)),
                               shape=(len(users), len(items)),
                               dtype=np.float32)
        self.UI = normalize(UI, norm="l2", axis=1, copy=False)
        self.item_sim = (self.UI.T @ self.UI).tocsr()
        self.item_sim.setdiag(0.0)
        self.item_sim.eliminate_zeros()

    # ────────────────────────────────────────────────────────────────────
    def get_scores_for_user(self, user_id: int) -> Dict[Tuple[str, int], float]:
        if user_id not in self.user2idx or self.item_sim.shape[0] == 0:
            return {}
        uidx = self.user2idx[user_id]
        scores_vec = self.UI.getrow(uidx) @ self.item_sim
        arr = np.asarray(scores_vec.todense()).ravel()
        idxs = np.where(arr > 0)[0]
        return { self.idx2item[i]: float(arr[i]) for i in idxs }
