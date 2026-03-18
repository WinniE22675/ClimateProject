import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from dotenv import load_dotenv, find_dotenv

from database.database import get_db
from database.models import User

# ==========================================
# 1. Load Environment Variables
# ==========================================
load_dotenv(find_dotenv())

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback_secret_key_if_env_missing")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# ==========================================
# 2. Define the Security Scheme
# ==========================================
# OAuth2PasswordBearer tells FastAPI to look for the token in the Authorization header.
# The 'tokenUrl' is the endpoint where users can login to get this token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ==========================================
# 3. Main Dependency Function (The Security Guard)
# ==========================================
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Dependency that extracts the JWT token, verifies it, 
    and returns the current logged-in user's information.
    """
    
    # Pre-define the exception to be raised if validation fails at any point
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Step 1: Decode the token using our secret key
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Step 2: Extract the user ID (subject) from the payload
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        # Raised if the token is expired, tampered with, or invalid
        raise credentials_exception
        
    # Step 3: Query the database to ensure the user actually exists
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if user is None:
        raise credentials_exception
        
    # Step 4: Return a dictionary containing user details
    # This matches the format expected by 'dataset_routes.py' (current_user["id"])
    return {
        "id": str(user.id),
        "email": str(user.email)
    }