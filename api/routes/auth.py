from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
import uuid
import random
import string
import redis
import os
import jwt
import re
from datetime import datetime, timedelta
from azure.communication.email import EmailClient
from azure.core.credentials import AzureKeyCredential

from agir_db.db.session import get_db
from agir_db.models.user import User

# Get environment variables
EMAIL_CONNECTION_STRING = os.environ.get("EMAIL_CONNECTION_STRING")
EMAIL_FROM = os.environ.get("EMAIL_FROM")
REDIS_URL = os.environ.get("REDIS_URL")
JWT_SECRET = os.environ.get("JWT_SECRET")

# Parse JWT expiration time with units (e.g. "7d" for 7 days)
def parse_expiration_time(expiration_str: str) -> int:
    """Parse expiration time with units (s, m, h, d) to seconds"""
    if not expiration_str:
        return 3600  # Default to 1 hour

    match = re.match(r"^(\d+)([smhd])?$", expiration_str)
    if not match:
        return 3600  # Default to 1 hour if format is invalid

    value, unit = match.groups()
    value = int(value)
    
    if unit == "s" or unit is None:
        return value
    elif unit == "m":
        return value * 60
    elif unit == "h":
        return value * 3600
    elif unit == "d":
        return value * 86400
    
    return 3600  # Default to 1 hour if unit is invalid

JWT_EXPIRES_IN = parse_expiration_time(os.environ.get("JWT_EXPIRES_IN", "3600"))

# Initialize Redis client
try:
    redis_client = redis.from_url(REDIS_URL) if REDIS_URL else None
except Exception as e:
    print(f"Redis connection error: {e}")
    redis_client = None

# Initialize Azure Email client
try:
    email_client = EmailClient.from_connection_string(EMAIL_CONNECTION_STRING) if EMAIL_CONNECTION_STRING else None
except Exception as e:
    print(f"Email client initialization error: {e}")
    email_client = None

router = APIRouter()

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

def create_jwt_token(user_id: str) -> str:
    """Create a JWT token for the user"""
    expires = datetime.utcnow() + timedelta(seconds=JWT_EXPIRES_IN)
    payload = {
        "sub": str(user_id),
        "exp": expires
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token

async def send_email(to_email: str, code: str):
    """Send an email using Azure Communication Services"""
    message = {
        "content": {
            "subject": "AGIR Verification Code",
            "plainText": f"Your verification code is: {code}",
            "html": f"<html><body><h1>Your verification code is: {code}</h1></body></html>"
        },
        "recipients": {
            "to": [{"address": to_email}]
        },
        "senderAddress": EMAIL_FROM
    }
    
    try:
        # Use begin_send instead of send
        poller = email_client.begin_send(message)
        result = poller.result()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@router.post("/send-code")
async def send_verification_code(
    email: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Send a verification code to the user's email"""
    if not email or '@' not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address"
        )
    
    # Generate a verification code
    code = generate_verification_code()
    
    # In-memory fallback for testing when Redis is unavailable
    verification_codes = {}
    
    # Store the code in Redis with expiration (30 minutes) or fallback to in-memory
    if redis_client:
        try:
            redis_client.setex(
                f"verification:{email}",
                1800,  # 30 minutes in seconds
                code
            )
        except Exception as e:
            print(f"Redis error: {e}")
            # Fall back to in-memory storage
            verification_codes[email] = {
                "code": code,
                "expires_at": datetime.utcnow() + timedelta(minutes=30)
            }
    else:
        # Use in-memory storage if Redis is not available
        verification_codes[email] = {
            "code": code,
            "expires_at": datetime.utcnow() + timedelta(minutes=30)
        }
    
    # Send email using Azure services or fall back to console output
    if email_client:
        email_sent = await send_email(email, code)
        if not email_sent:
            print(f"Verification code for {email}: {code}")
    else:
        # Fallback to console output for testing
        print(f"Verification code for {email}: {code}")
    
    return {"message": "Verification code sent to your email"}

@router.post("/verify")
async def verify_code(
    email: str = Body(..., embed=True),
    code: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Verify the code and log in or create a user account"""
    # In-memory fallback for testing
    verification_codes = {}
    
    # Get the code from Redis or fallback storage
    stored_code = None
    if redis_client:
        try:
            stored_code = redis_client.get(f"verification:{email}")
        except Exception as e:
            print(f"Redis error: {e}")
            # Check in-memory storage if Redis fails
            if email in verification_codes:
                stored_data = verification_codes[email]
                if datetime.utcnow() <= stored_data["expires_at"]:
                    stored_code = stored_data["code"]
    else:
        # Use in-memory storage if Redis is not available
        if email in verification_codes:
            stored_data = verification_codes[email]
            if datetime.utcnow() <= stored_data["expires_at"]:
                stored_code = stored_data["code"]
    
    if not stored_code:
        # For development/testing, accept any code if both Redis and in-memory don't have the code
        if os.environ.get("ENVIRONMENT") == "development":
            print(f"Development mode: accepting any code for {email}")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No verification code was sent to this email or the code has expired"
            )
    elif isinstance(stored_code, bytes) and stored_code.decode('utf-8') != code:
        # Redis returns bytes
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    elif isinstance(stored_code, str) and stored_code != code:
        # In-memory returns string
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Code is valid, check if user exists
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Create a new user
        username = email.split('@')[0]
        user = User(
            email=email,
            username=username,
            first_name=username,  # Default first name
            last_name="",
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Clear the verification code
    if redis_client:
        try:
            redis_client.delete(f"verification:{email}")
        except Exception as e:
            print(f"Redis error when deleting code: {e}")
    
    if email in verification_codes:
        del verification_codes[email]
    
    # Generate JWT token
    token = create_jwt_token(user.id)
    
    # Return user info and token
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "token": token
    }

@router.post("/validate-token")
async def validate_token(
    token: str = Body(..., embed=True)
):
    """Validate a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return {"valid": True, "user_id": payload["sub"]}
    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"valid": False, "error": "Invalid token"} 