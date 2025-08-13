import os, argparse, logging
from datetime import datetime
from dotenv import load_dotenv
import tmdbsimple as tmdb
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Movie

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
log = logging.getLogger(__name__)

def init_db(url: str):
    eng = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(bind=eng)
    return sessionmaker(bind=eng, autocommit=False, autoflush=False)

def load_movies(pages: int, SessionLocal):
    s = SessionLocal()
    try:
        for p in range(1, pages+1):
            log.info("TMDb popular page %s/%s", p, pages)
            resp = tmdb.Movies().popular(page=p)
            for it in resp.get("results", []):
                tid = it["id"]
                if s.query(Movie).filter_by(tmdb_movie_id=tid).first(): continue
                rd = it.get("release_date") or None
                rd_parsed = datetime.fromisoformat(rd).date() if rd else None
                s.add(Movie(
                    tmdb_movie_id=tid,
                    title=it.get("title") or it.get("name"),
                    release_date=rd_parsed,
                    overview=it.get("overview"),
                    poster_path=it.get("poster_path"),
                ))
            s.commit()
    except Exception:
        log.exception("Error, rollback"); s.rollback(); raise
    finally:
        s.close()

def main():
    load_dotenv()
    tmdb.API_KEY = os.getenv("TMDB_API_KEY")
    url = os.getenv("DATABASE_URL")
    if not tmdb.API_KEY: raise SystemExit("TMDB_API_KEY missing")
    if not url: raise SystemExit("DATABASE_URL missing")

    SessionLocal = init_db(url)
    ap = argparse.ArgumentParser()
    ap.add_argument("-p","--pages", type=int, default=10)
    args = ap.parse_args()
    load_movies(args.pages, SessionLocal)
    print("Done.")

if __name__ == "__main__":
    main()
