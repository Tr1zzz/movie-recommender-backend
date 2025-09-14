import os, argparse, logging
from datetime import datetime
from dotenv import load_dotenv
import tmdbsimple as tmdb
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import TvShow

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
log = logging.getLogger(__name__)

def init_db(url: str):
    eng = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(bind=eng)
    return sessionmaker(bind=eng, autocommit=False, autoflush=False)

def load_tv_shows(pages: int, SessionLocal):
    s = SessionLocal()
    try:
        tv = tmdb.TV()
        for p in range(1, pages + 1):
            log.info("TMDb popular TV page %s/%s", p, pages)
            resp = tv.popular(page=p)
            for it in resp.get("results", []):
                tid = it["id"]
                if s.query(TvShow).filter_by(tmdb_tv_id=tid).first():
                    continue
                fa = it.get("first_air_date") or None
                fa_parsed = datetime.fromisoformat(fa).date() if fa else None
                s.add(TvShow(
                    tmdb_tv_id=tid,
                    name=it.get("name") or it.get("original_name") or "",
                    first_air=fa_parsed,
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
    ap.add_argument("-p", "--pages", type=int, default=10)
    args = ap.parse_args()
    load_tv_shows(args.pages, SessionLocal)
    print("Done.")

if __name__ == "__main__":
    main()
