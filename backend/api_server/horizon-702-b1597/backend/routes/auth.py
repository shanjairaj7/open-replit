"""
Authentication Service - Complete Auth System in One File
Contains routes, business logic, database operations, and JWT handling
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, List

# Database imports
from json_db import JsonDBSession, get_db

# Router setup
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# JWT and Password settings
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pydantic Models for Auth
class AuthUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)

class AuthUserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserResponse

# Auth Utilities
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
        full_name = payload.get("full_name")
        if user_id is None:
            return None
        return {"user_id": int(user_id), "full_name": full_name}
    except JWTError:
        return None

# Dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: JsonDBSession = Depends(get_db)
) -> AuthUserResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception
    
    user_data = db.db.find_one("users", id=token_data["user_id"])
    if user_data is None:
        raise credentials_exception
    
    return AuthUserResponse(**user_data)

def get_current_active_user(current_user: AuthUserResponse = Depends(get_current_user)) -> AuthUserResponse:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Routes
@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(user_data: AuthUserCreate, db: JsonDBSession = Depends(get_db)):
    # Check if email exists
    if db.db.exists("users", email=user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = hash_password(user_data.password)
    user_record = db.db.insert("users", {
        "full_name": user_data.full_name,
        "email": user_data.email,
        "hashed_password": hashed_password,
        "is_active": True
    })
    
    db_user = AuthUserResponse(**user_record)
    
    # Create token
    access_token = create_access_token(
        data={"sub": str(db_user.id), "full_name": db_user.full_name}
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=db_user
    )

@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: JsonDBSession = Depends(get_db)):
    user_data = db.db.find_one("users", email=login_data.email)
    
    if not user_data or not verify_password(login_data.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user_data["is_active"]:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    user = AuthUserResponse(**user_data)
    
    access_token = create_access_token(
        data={"sub": str(user.id), "full_name": user.full_name}
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user
    )

@router.get("/profile", response_model=AuthUserResponse)
def get_profile(current_user: AuthUserResponse = Depends(get_current_user)):
    return current_user

@router.post("/logout")
def logout(current_user: AuthUserResponse = Depends(get_current_user)):
    return {"message": f"User {current_user.full_name} logged out successfully"}