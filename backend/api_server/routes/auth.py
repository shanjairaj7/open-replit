from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import EmailStr, BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional
import os
import secrets

from json_db import db
from models import UserCreate, UserResponse
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return {"user_id": int(user_id)}
    except JWTError:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = verify_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception
    user_data = db.find_one("users", id=token_data["user_id"])
    if user_data is None or not user_data.get("is_active", True):
        raise credentials_exception
    return user_data

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserCreate):
    if db.exists("users", email=user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = hash_password(user_data.password)
    user_record = db.insert("users", {
        "email": user_data.email,
        "hashed_password": hashed_password,
        "name": user_data.name,
        "is_active": True,
        "organisation_id": None,
        "role": "owner"
    })
    access_token = create_access_token(data={"sub": str(user_record["id"])})
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(**user_record)
    )

@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin):
    user_data = db.find_one("users", email=login_data.email)
    if not user_data or not verify_password(login_data.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    if not user_data.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token = create_access_token(data={"sub": str(user_data["id"])})
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(**user_data)
    )

@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)

@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    return {"message": f"User {current_user['email']} logged out successfully"}