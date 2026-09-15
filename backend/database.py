import os
import re
import logging
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from fastapi import HTTPException, status

load_dotenv()

logger = logging.getLogger(__name__)

# Hardcoded production fallback for MongoDB Atlas so Render and cloud deployments always connect
DEFAULT_MONGODB_URL = "mongodb+srv://byus_admin:byus717@byus.uuizsni.mongodb.net/byus?retryWrites=true&w=majority"

# Sanitize URL: strip any trailing whitespace, newlines, or tabs from dashboard copy-paste
_raw_mongo_url = (os.getenv("MONGODB_URL") or "").strip() or DEFAULT_MONGODB_URL
MONGODB_URL = re.sub(r"\s+", "", _raw_mongo_url)

JWT_SECRET = os.getenv("JWT_SECRET", "byus2026RadiantTanmaySecretKey$#@NMIMSIndore")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", 168))

client = None
db = None

async def connect_db():
    global client, db
    if not MONGODB_URL:
        raise RuntimeError(
            "FATAL: MONGODB_URL is not set. MongoDB Atlas connection is required."
        )

    print(f"[Database] Connecting to MongoDB Atlas...")
    client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=10000)
    
    # Verify server connectivity
    await client.admin.command('ping')
    
    # Use 'byus' database directly
    db = client.byus
    
    # Create required indexes
    await db.users.create_index("email", unique=True)
    await db.reports.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await db.reports.create_index("session_id", unique=True)
    print("[Database] Connected successfully to MongoDB Atlas (database: byus)")

async def disconnect_db():
    global client
    if client:
        client.close()
        print("[Database] Disconnected from MongoDB")

def get_db():
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not available."
        )
    return db
