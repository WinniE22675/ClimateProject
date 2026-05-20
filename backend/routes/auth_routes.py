from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv, find_dotenv
from passlib.context import CryptContext
from jose import jwt, JWTError

from database.database import get_db
from database.models import User

# Automatically search for .env file in current and parent directories
load_dotenv(find_dotenv())

# ==========================================
# 1. Configuration & Security Settings
# ==========================================
# In production, SECRET_KEY MUST come from .env file
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback_secret_key_if_env_missing")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

ADMIN_CODE = os.getenv("ADMIN_CODE")

# Setup for password hashing using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ==========================================
# 2. Helper Functions
# ==========================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if the provided plain password matches the hashed password in the database."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a plain text password for secure storage."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a JWT token containing user data (e.g., user_id and role)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ==========================================
# 3. Pydantic Schemas (Data Validation)
# ==========================================
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = "viewer"
    admin_code: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# ==========================================
# 4. API Routes
# ==========================================
router = APIRouter()

# @router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
# def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
#     """
#     Register a new user, save their role, and return an access token.
#     """
#     # Check if user already exists
#     existing_user = db.query(User).filter(User.email == user_data.email).first()
#     if existing_user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Email is already registered"
#         )
    
#     # Validate and assign role securely (prevent users from sending fake roles like 'admin_super')
#     valid_roles = ["viewer", "analyst"]
#     assigned_role = user_data.role if user_data.role in valid_roles else "viewer"
#     if assigned_role == "analyst":
#         if not ADMIN_CODE or user_data.admin_code != ADMIN_CODE:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Invalid Administrator Code. You cannot register as an Analyst."
#             )
    
#     # Create new user with hashed password
#     hashed_pw = get_password_hash(user_data.password)
#     new_user = User(email=user_data.email, hashed_password=hashed_pw, role=assigned_role)
    
#     # Save to database
#     db.add(new_user)
#     db.commit()
#     db.refresh(new_user)
    
#     # Generate token WITH role included in the payload
#     access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = create_access_token(
#         data={"sub": str(new_user.id), "role": new_user.role}, 
#         expires_delta=access_token_expires
#     )
    
#     return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=TokenResponse)
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a JWT access token containing their role.
    """
    # Find user by email
    user = db.query(User).filter(User.email == user_data.email).first()
    
    # Check if user exists and password is correct
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate token WITH role included in the payload
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}