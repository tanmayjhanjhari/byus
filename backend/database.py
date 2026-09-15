from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from fastapi import HTTPException, status
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MONGODB_URL = os.getenv("MONGODB_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "byus_default_secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", 168))

client = None
db = None

async def connect_db():
    global client, db
    if not MONGODB_URL:
        print("[Database] MONGODB_URL not configured. Running in memory-only mode without MongoDB.")
        client = None
        db = None
        return

    try:
        # Set a 5-second timeout so app doesn't hang if MongoDB URL is wrong or unreachable
        client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
        await client.admin.command('ping')
        
        # Resolve database
        default_db = client.get_default_database()
        db = default_db if default_db is not None else client.byus
        
        # Create indexes
        await db.users.create_index("email", unique=True)
        await db.reports.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        await db.reports.create_index("session_id", unique=True)
        print("[Database] Connected successfully to MongoDB Atlas")
    except Exception as exc:
        print(f"[Database] WARNING: Could not connect to MongoDB ({exc}). Running in in-memory session mode.")
        client = None
        db = None

async def disconnect_db():
    global client
    if client:
        client.close()
        print("[Database] Disconnected from MongoDB")

def get_db():
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. MONGODB_URL is not configured or MongoDB cluster is unreachable."
        )
    return db
