from fastapi import FastAPI

from app.api import router as api_router
from app.db.database import db
from app.settings import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
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


@app.get("/db-test")
def db_test():
    collections = db.list_collection_names()
    return {
        "message": "MongoDB connection successful",
        "database": db.name,
        "collections": collections,
    }
