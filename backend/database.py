from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
import os
from dotenv import load_dotenv
load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "byus_default_secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", 168))

client = None
db = None

async def connect_db():
    global client, db
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client.byus
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.reports.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await db.reports.create_index("session_id", unique=True)
    print("[Database] Connected to MongoDB Atlas")

async def disconnect_db():
    global client
    if client:
        client.close()
        print("[Database] Disconnected from MongoDB")

def get_db():
    return db
