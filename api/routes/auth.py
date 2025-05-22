from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
import uuid
import random
import string
from datetime import datetime, timedelta

from agir_db.db.session import get_db
from agir_db.models.user import User

# In a real implementation, these would use Azure services and Redis
# This is a simple in-memory store for demonstration purposes
verification_codes = {}

router = APIRouter()

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

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
    
    # Store the code with expiration (30 minutes)
    verification_codes[email] = {
        "code": code,
        "expires_at": datetime.utcnow() + timedelta(minutes=30)
    }
    
    # In a real implementation, this would send an email using Azure services
    # For now, we just log it
    print(f"Verification code for {email}: {code}")
    
    return {"message": "Verification code sent to your email"}

@router.post("/verify")
async def verify_code(
    email: str = Body(..., embed=True),
    code: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Verify the code and log in or create a user account"""
    if email not in verification_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verification code was sent to this email"
        )
    
    stored_data = verification_codes[email]
    
    # Check if the code has expired
    if datetime.utcnow() > stored_data["expires_at"]:
        del verification_codes[email]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired"
        )
    
    # Check if the code matches
    if stored_data["code"] != code:
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
            role="user",
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Clear the verification code
    del verification_codes[email]
    
    # Return user info
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role
    } 