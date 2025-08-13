from fastapi import Depends
from sqlalchemy.orm import Session
from .database import get_db
from .recommenders.hybrid import get_recommender, _meta_key

def recommender_dep(db: Session = Depends(get_db)):
    return get_recommender(db, _meta_key())