from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, SessionLocal, engine
from app.models import Category
from app.routers import auth, categories, service_requests

from app.routers import provider_jobs
from app.routers import provider_profile

from app.routers import reviews
from app.routers import dashboard
from app.routers import history
from app.routers import providers

Base.metadata.create_all(bind=engine)


def seed_categories():
    db = SessionLocal()
    try:
        for name in ["Plumbing", "Electrical", "Appliance Repair", "Computer Repair"]:
            if not db.query(Category).filter(Category.name == name).first():
                db.add(Category(name=name))
        db.commit()
    finally:
        db.close()


seed_categories()

app = FastAPI(title="FixTrail API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8001",
        "http://localhost:8001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(service_requests.router)
app.include_router(provider_jobs.router)
app.include_router(provider_profile.router)
app.include_router(reviews.router)
app.include_router(dashboard.router)
app.include_router(history.router)
app.include_router(providers.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}