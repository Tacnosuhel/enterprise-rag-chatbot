# src/security/jwt_auth.py
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Secret key & token config
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "finsolve_enterprise_secure_production_secret_key_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()

def hash_password(password: str) -> str:
    """Hashes a password using pure native bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain text password against bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# Enterprise User Store with Hashed Passwords
USERS_DB: Dict[str, dict] = {
    "alice": {
        "username": "alice",
        "name": "Alice Johnson",
        "hashed_password": hash_password("tech123"),
        "role": "engineer",
        "allowed_departments": ["technology"]
    },
    "bob": {
        "username": "bob",
        "name": "Bob Miller",
        "hashed_password": hash_password("hr123"),
        "role": "hr",
        "allowed_departments": ["hr"]
    },
    "carol": {
        "username": "carol",
        "name": "Carol Davis",
        "hashed_password": hash_password("finance123"),
        "role": "finance",
        "allowed_departments": ["finance"]
    },
    "admin": {
        "username": "admin",
        "name": "Super Admin",
        "hashed_password": hash_password("admin123"),
        "role": "admin",
        "allowed_departments": ["all"]
    }
}


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Checks credentials and returns user if valid."""
    user = USERS_DB.get(username.lower().strip())
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token containing user claims."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    FastAPI dependency: Extracts and verifies JWT from Authorization header.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = USERS_DB.get(username)
    if user is None:
        raise credentials_exception

    return {
        "username": user["username"],
        "name": user["name"],
        "role": user["role"],
        "allowed_departments": user["allowed_departments"]
    }