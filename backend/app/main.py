from fastapi import FastAPI
from app.db.database import db

app = FastAPI(title="Kocaeli News Map API")

@app.get("/")
def root():
    return {"message": "API is running"}

@app.get("/db-test")
def db_test():
    collections = db.list_collection_names()
    return {
        "message": "MongoDB connection successful",
        "database": db.name,
        "collections": collections
    }