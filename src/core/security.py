import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

# Configuration - In a real app, load these from environment variables
SECRET_KEY = "a_very_secret_key_that_should_be_in_env"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict) -> str:
    """
    Generates a new JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> Optional[dict]:
    """
    Verifies the JWT access token and returns the payload if valid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        # This could be ExpiredSignatureError, InvalidTokenError, etc.
        # We can log the specific error here if needed.
        return None
