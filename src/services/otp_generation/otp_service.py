import random
import string
import datetime
from typing import Dict, Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, select

from src.datamodel.database.userauth.AuthenticationTables import VerificationOTP, VerifiedIdentifier
from src.core.authentication.cred_load import SECRET_KEY, ALGORITHM, RESET_PASSWORD_EXPIRE_MINUTES
# from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class OTPService:
    """Service for generating and validating OTPs for email and phone verification"""
    
    def __init__(self):
        self._otp_expiry_minutes = 15  # 15 minutes
    
    async def generate_otp(self, identifier: str, type: str, db: AsyncSession) -> str:
        """
        Generate a 6-digit OTP for the given email or phone
        
        Args:
            identifier: Email or phone number
            type: 'email' or 'phone'
            db: Database session
            
        Returns:
            The generated OTP
        """
        # Generate a 6-digit OTP
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Calculate expiry time
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=self._otp_expiry_minutes)
        
        # Delete any existing OTPs for this identifier
        query = select(VerificationOTP).where(
            VerificationOTP.identifier == identifier,
            VerificationOTP.type == type
        )
        result = await db.execute(query)
        existing_otps = result.scalars().all()

        for existing_otp in existing_otps:
            await db.delete(existing_otp)
        
        # Create new OTP record
        otp_record = VerificationOTP(
            identifier=identifier,
            otp=otp,
            type=type,
            expires_at=expires_at
        )
        
        db.add(otp_record)
        await db.commit()
        
        logger.info(f"Generated OTP for {type} {identifier}")
        return otp
    
    async def verify_otp(self, identifier: str, otp: str, type: str, db: AsyncSession) -> bool:
        """
        Verify if the provided OTP is valid for the identifier
        
        Args:
            identifier: Email or phone number
            otp: The OTP to verify
            type: 'email' or 'phone'
            db: Database session
            
        Returns:
            True if OTP is valid, False otherwise
        """
        # Find the OTP record
        query = select(VerificationOTP).where(
            VerificationOTP.identifier == identifier,
            VerificationOTP.otp == otp,
            VerificationOTP.type == type,
            VerificationOTP.is_used == False
        )
        result = await db.execute(query)
        otp_record = result.scalar_one_or_none()
        
        if not otp_record:
            logger.warning(f"No valid OTP found for {type} {identifier}")
            return False
        
        # Check if OTP is expired
        if otp_record.is_expired():
            logger.warning(f"OTP expired for {type} {identifier}")
            otp_record.is_used = True
            await db.commit()
            return False
        
        # Mark OTP as used
        otp_record.is_used = True
        
        # Create or update verified identifier record
        query = select(VerifiedIdentifier).where(
            VerifiedIdentifier.identifier == identifier,
            VerifiedIdentifier.type == type
        )
        result = await db.execute(query)
        verified = result.scalar_one_or_none()
        
        if not verified:
            verified = VerifiedIdentifier(
                identifier=identifier,
                type=type
            )
            db.add(verified)
        else:
            verified.verified_at = datetime.datetime.utcnow()
        
        await db.commit()
        logger.info(f"OTP verified successfully for {type} {identifier}")
        return True
    
    async def is_verified(self, identifier: str, type: str, db: AsyncSession) -> bool:
        """
        Check if an identifier has been verified
        
        Args:
            identifier: Email or phone number
            type: 'email' or 'phone'
            db: Database session
            
        Returns:
            True if identifier is verified, False otherwise
        """
        query = select(VerifiedIdentifier).where(
            VerifiedIdentifier.identifier == identifier,
            VerifiedIdentifier.type == type
        )
        result = await db.execute(query)
        verified = result.scalar_one_or_none()
        
        return verified is not None
    
    async def link_to_user(self, identifier: str, type: str, user_id: str, db: AsyncSession) -> bool:
        """
        Link a verified identifier to a user
        
        Args:
            identifier: Email or phone number
            type: 'email' or 'phone'
            user_id: User ID to link to
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        query = select(VerifiedIdentifier).where(
            VerifiedIdentifier.identifier == identifier,
            VerifiedIdentifier.type == type
        )
        result = await db.execute(query)
        verified = result.scalar_one_or_none()
        
        if not verified:
            logger.warning(f"{type.capitalize()} {identifier} not verified")
            return False
        
        verified.user_id = user_id
        await db.commit()
        logger.info(f"Linked {type} {identifier} to user {user_id}")
        return True
    
        # Helper functions for token generation and verification
    def generate_password_reset_token(self , user_id: str) -> str:
        """
        Generate a JWT token for password reset
        """
        expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=int(RESET_PASSWORD_EXPIRE_MINUTES))
        # # Calculate expiry time
        # expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=self._otp_expiry_minutes)
        to_encode = {
            "sub": str(user_id),
            "exp": expires,
            "type": "password_reset"
        }
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def verify_password_reset_token(self, token: str) -> Optional[str]:
        """
        Verify the password reset token and return the user_id if valid
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "password_reset":
                return None
            user_id = payload.get("sub")
            return user_id
        except JWTError:
            return None


# Create a singleton instance
otp_service = OTPService()



