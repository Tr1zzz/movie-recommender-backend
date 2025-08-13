from __future__ import annotations
import numpy as np
from scipy import sparse
from sklearn.preprocessing import normalize
from sqlalchemy.orm import Session
from typing import Dict
from ..models import UserMovieAction, Movie

class ItemItemCF:
    def __init__(self, db: Session):
        self._build(db)

    def _build(self, db: Session):
        actions = db.query(UserMovieAction).all()
        items   = [m[0] for m in db.query(Movie.tmdb_movie_id).all()]
        items   = sorted(set(items))
        users   = sorted({a.user_id for a in actions})

        self.user2idx = {u:i for i,u in enumerate(users)}
        self.item2idx = {m:i for i,m in enumerate(items)}
        self.idx2item = {i:m for m,i in self.item2idx.items()}

        if not users or not items:
            self.UI = sparse.csr_matrix((0,0)); self.item_sim = sparse.csr_matrix((0,0)); return

        rows, cols, data = [], [], []
        for a in actions:
            if a.tmdb_movie_id not in self.item2idx: continue
            rows.append(self.user2idx[a.user_id]); cols.append(self.item2idx[a.tmdb_movie_id])
            data.append(float(a.rating or 1.0))

        UI = sparse.csr_matrix((data,(rows,cols)), shape=(len(users), len(items)), dtype=np.float32)
        self.UI = normalize(UI, norm="l2", axis=1, copy=False)
        self.item_sim = (self.UI.T @ self.UI).tocsr()
        self.item_sim.setdiag(0.0); self.item_sim.eliminate_zeros()

    def score_for_user(self, user_id: int) -> Dict[int, float]:
        if user_id not in self.user2idx or self.item_sim.shape[0] == 0: return {}
        u = self.user2idx[user_id]
        scores_vec = self.UI.getrow(u) @ self.item_sim
        scores = np.asarray(scores_vec.todense()).ravel()
        idxs = np.where(scores > 0)[0]
        return { self.idx2item[i]: float(scores[i]) for i in idxs }
