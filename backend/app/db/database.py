from dotenv import load_dotenv
load_dotenv()

from pymongo import MongoClient
import os

MONGO_URL = os.getenv("MONGO_URL")
MONGO_DB = os.getenv("MONGO_DB")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]