from pymongo import MongoClient

from app.settings import settings


client = MongoClient(
    settings.mongo_url,
    serverSelectionTimeoutMS=5000,
)

db = client[settings.mongo_db]
