from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base,engine
from app.routers import auth

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FixTrail API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://127.0.0.1:3000",
    "http://localhost:3000", 
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:8001",
    "http://localhost:8001",],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
