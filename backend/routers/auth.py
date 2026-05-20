from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from datetime import datetime
from bson import ObjectId
from typing import Optional
from ..database import get_db
from ..services.auth_service import (
    hash_password, verify_password,
    create_token, decode_token, serialize_doc
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login",
                                     auto_error=False)

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> Optional[dict]:
    """
    Returns user dict if valid token provided.
    Returns None if no token (guest user) — allows optional auth.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    if not payload:
        return None
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        return None
    return serialize_doc(user)

async def require_user(
    authorization: Optional[str] = Header(None)
) -> dict:
    """Use this dependency when login is REQUIRED."""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401,
                            detail="Login required to access this resource.")
    return user

@router.post("/register")
async def register(req: RegisterRequest):
    db = get_db()
    existing = await db.users.find_one({"email": req.email.lower()})
    if existing:
        raise HTTPException(status_code=400,
                            detail="An account with this email already exists.")
    user_doc = {
        "name": req.name.strip(),
        "email": req.email.lower().strip(),
        "password": hash_password(req.password),
        "created_at": datetime.utcnow(),
        "total_analyses": 0,
        "avg_audit_score": None,
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    token = create_token(user_id, req.email.lower())
    return {
        "token": token,
        "user": {
            "id": user_id,
            "name": req.name,
            "email": req.email.lower(),
        }
    }

@router.post("/login")
async def login(req: LoginRequest):
    db = get_db()
    user = await db.users.find_one({"email": req.email.lower()})
    if not user or not verify_password(req.password, user["password"]):
        raise HTTPException(status_code=401,
                            detail="Incorrect email or password.")
    user_id = str(user["_id"])
    token = create_token(user_id, req.email.lower())
    return {
        "token": token,
        "user": {
            "id": user_id,
            "name": user["name"],
            "email": user["email"],
            "total_analyses": user.get("total_analyses", 0),
            "avg_audit_score": user.get("avg_audit_score"),
        }
    }

@router.get("/me")
async def get_me(user: dict = Depends(require_user)):
    return user

@router.post("/logout")
async def logout():
    # JWT is stateless — client just deletes the token
    return {"message": "Logged out successfully."}
