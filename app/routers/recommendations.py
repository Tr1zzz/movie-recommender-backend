from typing import List, Dict
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import UserMovieAction
from ..recommender import ContentRecommender
from ..cf_recommender import CFRecommender

from ..utils.security import get_current_user  

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

ALPHA = 0.6  

@router.get("/for-you", response_model=List[int])
def for_you(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cf_scores = CFRecommender.get_cached(db).get_scores_for_user(current_user.id)
    cb_scores = ContentRecommender.get_cached(db).cb_scores_for_user(db, current_user.id)

    seen = {
        t for (t,) in db.query(UserMovieAction.tmdb_movie_id)
                        .filter(UserMovieAction.user_id == current_user.id)
                        .all()
    }

    ids = set(cf_scores) | set(cb_scores)
    blended: Dict[int, float] = {}
    for m in ids:
        if m in seen:
            continue
        blended[m] = ALPHA * cf_scores.get(m, 0.0) + (1.0 - ALPHA) * cb_scores.get(m, 0.0)

    top = sorted(blended.items(), key=lambda kv: kv[1], reverse=True)[:10]
    return [mid for (mid, _) in top]

@router.post("/retrain", status_code=status.HTTP_204_NO_CONTENT)
def retrain_models(
    _current_user = Depends(get_current_user),
    _db: Session = Depends(get_db),
):
    
    ContentRecommender.reset_cache()
    CFRecommender.reset_cache()
    return
