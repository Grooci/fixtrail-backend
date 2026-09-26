from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

DATABASE_URL = "postgresql://postgres:password@localhost:5432/fixtrail"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoFlush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

