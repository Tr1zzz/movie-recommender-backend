from typing import List, Dict, Tuple
import numpy as np
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import UserMovieAction, Movie, TvShow
from ..recommender import ContentRecommender
from ..cf_recommender import CFRecommender
from ..utils.security import get_current_user

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

ALPHA = 0.6

# ---------- MMR (Maximal Marginal Relevance) ----------
def mmr_rerank(
    candidates: List[Tuple[str, int]],
    emb_lookup: Dict[Tuple[str, int], np.ndarray],
    lambda_: float = 0.7,
    k: int = 30,
) -> List[Tuple[str, int]]:
   
    cands = [c for c in candidates if c in emb_lookup]
    if len(cands) <= 1:
        return cands[:k]

    X = np.vstack([emb_lookup[c] for c in cands])
    X_norm = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-8)
    sim = X_norm @ X_norm.T  # (n x n), diag ~ 1

    selected: List[int] = []
    remaining = list(range(len(cands)))

    first = remaining.pop(0)
    selected.append(first)

    while remaining and len(selected) < k:
      best_idx = None
      best_val = -1e9
      for r in remaining:
          rel = -r
          max_sim = max(sim[r, s] for s in selected)
          val = lambda_ * rel - (1.0 - lambda_) * max_sim
          if val > best_val:
              best_val = val
              best_idx = r
      selected.append(best_idx)
      remaining.remove(best_idx)

    return [cands[i] for i in selected[:k]]

@router.get("/for-you", response_model=List[int])
def for_you(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cf_scores: Dict[Tuple[str, int], float] = CFRecommender.get_cached(db).get_scores_for_user(current_user.id)
    cb_scores: Dict[Tuple[str, int], float] = ContentRecommender.get_cached(db).cb_scores_for_user(db, current_user.id)

    seen_ids = {
        t for (t,) in db.query(UserMovieAction.tmdb_movie_id)
                        .filter(UserMovieAction.user_id == current_user.id)
                        .all()
    }

    def is_seen(key: Tuple[str, int]) -> bool:
        _mt, tid = key
        return tid in seen_ids

    ids = set(cf_scores) | set(cb_scores)
    blended: Dict[Tuple[str, int], float] = {}
    for key in ids:
        if is_seen(key):
            continue
        blended[key] = ALPHA * cf_scores.get(key, 0.0) + (1.0 - ALPHA) * cb_scores.get(key, 0.0)

    if not blended:
        return []

    prelim = sorted(blended.items(), key=lambda kv: kv[1], reverse=True)
    candidate_keys: List[Tuple[str, int]] = [k for k, _ in prelim[:200]]

    cr = ContentRecommender.get_cached(db)
    emb_lookup: Dict[Tuple[str, int], np.ndarray] = {}
    if getattr(cr, "mat", None) is not None and cr.mat.shape[0] > 0:
        for key in candidate_keys:
            idx = cr.tmdb2idx.get(key)
            if idx is not None:
                emb_lookup[key] = cr.mat[idx].toarray().ravel()

    if len(emb_lookup) >= 2:
        reranked = mmr_rerank(candidate_keys, emb_lookup, lambda_=0.7, k=30)
    else:
        reranked = candidate_keys[:30]

    result_movie_ids: List[int] = []
    for mt, tid in reranked:
        if mt == "movie":
            result_movie_ids.append(tid)
    if len(result_movie_ids) < 10:
        for mt, tid in candidate_keys:
            if mt == "movie" and tid not in result_movie_ids:
                result_movie_ids.append(tid)
            if len(result_movie_ids) >= 10:
                break

    return result_movie_ids[:10]


@router.post("/retrain", status_code=status.HTTP_204_NO_CONTENT)
def retrain_models(
    _current_user = Depends(get_current_user),
    _db: Session = Depends(get_db),
):
    ContentRecommender.reset_cache()
    CFRecommender.reset_cache()
    return
