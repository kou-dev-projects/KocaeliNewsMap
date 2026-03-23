from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.db.database import db
from app.settings import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    return {
        "message": "API is running",
        "name": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "name": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
    }


@app.get("/db-test")
def db_test():
    collections = db.list_collection_names()
    return {
        "message": "MongoDB connection successful",
        "database": db.name,
        "collections": collections,
    }
