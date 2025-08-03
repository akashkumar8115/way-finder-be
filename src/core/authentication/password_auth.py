from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
import logging
import re
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi import Depends, FastAPI, HTTPException, status, APIRouter, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.authentication.cred_load import (
    SESSION_COOKIE_NAME,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from src.core.authentication.authentication import (
    authenticate_user,
    login_flow,
    get_password_hash,

    get_current_user,
    get_user_by_uuid,
    verify_user_identifiers,
    link_user_identifiers
)
from src.core.database.dbs.getdb import postresql as db
from src.datamodel.datavalidation.user import User, UserSignUp, UserLogin, Token
from src.core.database.curd.user import add_user, DuplicateError , get_user
from src.core.authentication.authentication import verify_password, get_token_payload
from src.datamodel.database.userauth.AuthenticationTables import Role


from src.services.otp_generation.otp_service import otp_service
from src.services.email.email_service import send_email_verification_otp, send_password_reset_email, welcome_email
from src.services.email.sms_service import send_phone_verification_otp
from src.datamodel.database.userauth.AuthenticationTables import VerifiedIdentifier
from sqlalchemy import select


# initializing logging
logger = logging.getLogger(__name__)

password_auth = APIRouter()
 
# @password_auth.post("/sign_up", summary="Register a user", tags=["Auth"])
@password_auth.post(
    "/signup", response_model=User, summary="Register a user", tags=["Auth"]
)
async def create_user(user_signup: UserSignUp, db: AsyncSession = Depends(db)):
    """
    Registers a user.
    """
    # Get phone number if it exists
    phone_number = getattr(user_signup, 'phone_number', None)
        
    # Verify email and phone
    await verify_user_identifiers(user_signup.email, phone_number, db)


    # if hasattr(user_signup, 'phone_number') and user_signup.phone_number is None:
    #     user_signup.phone_number = None  # Explicitly set to None

    user_signup.password = get_password_hash(user_signup.password)
    try:
        access_token = await login_flow(user=user_signup, db=db, auth_flow="signup")


        # Get the newly created user
        user = await get_user(db, user_signup.email)
        if user:
            # Link verified identifiers to the user
            await link_user_identifiers(user.user_uuid, user_signup.email, phone_number, db)
        else:
            logger.error(f"User not found after creation: {user_signup.email}")


        redirect_url = "/"
         
        response = JSONResponse({"redirect_url": redirect_url})
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=access_token,
            httponly=True,
            secure=True,
            samesite="none",
        )

        # Send welcome email
        welcome_email(user_signup.email)

        
        return response
    except HTTPException as http_exc:
        if http_exc.status_code == status.HTTP_409_CONFLICT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User already exists."
            )
        else:
            raise http_exc  # Re-raise other HTTP exceptions
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"{e}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred. Report this message to support: {e}",
        )


@password_auth.post("/passauth", summary="Login as a user", tags=["Auth"])
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(db),
):  # -> Token:
    # @router.post("/login", summary="Login as a user", tags=["Auth"])
    # asyc def login(response: RedirectResponse, username: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(db)):
    # use cookie
    try:
        user = UserLogin(
            username=form_data.username,
            password=form_data.password,
            login_on=datetime.now(timezone.utc),
        )
        access_token = await login_flow(user=user, db=db, auth_flow="login")
        # Determine Redirect Based on Role
        # user_stored = await get_user(db, user.username, user.provider)
        # role_id = user_stored.role_id if hasattr(user_stored, "role_id") else "user"
        user_stored = get_token_payload(access_token)
        role_id = user_stored["role_id"]
        # Role-Based Redirect
        redirect_url = "/"
        
        #Create user data to include in response
        user_data = {
            "user_uuid": user_stored["user_uuid"],
            "username": user_stored["username"],
            "role_id": role_id,
        }
        response = JSONResponse({"redirect_url": redirect_url})
        # Set the session cookie with the access token
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=access_token,
            httponly=True,
            secure=True,
            samesite="none",
        )

        return response
    except Exception as e:
        logger.error(f"Following error occured: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred. Report this message to support: {e}",
        )




class EmailVerificationRequest(BaseModel):
    email: EmailStr

class PhoneVerificationRequest(BaseModel):
    phone_country_code: str
    phone_number: str

class OTPVerificationRequest(BaseModel):
    identifier: str  # Email or phone number
    otp: str
    type: str  # 'email' or 'phone'

class VerificationStatus(BaseModel):
    email_verified: bool = False
    phone_verified: bool = False


@password_auth.post("/send-email-otp", summary="Send email verification OTP", tags=["Verification"])
async def send_email_otp(request: EmailVerificationRequest, db: AsyncSession = Depends(db)):
    """Send OTP to the provided email for verification"""
    try:
        # result = send_email_verification_otp(request.email)
        result = await send_email_verification_otp(request.email, db)
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {"message": "OTP sent to your email"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email OTP: {str(e)}")

@password_auth.post("/send-phone-otp", summary="Send phone verification OTP", tags=["Verification"])
async def send_phone_otp(request: PhoneVerificationRequest, db: AsyncSession = Depends(db)):
    """Send OTP to the provided phone number for verification"""
    try:
        # result = send_phone_verification_otp(request.phone_number)
        result = await send_phone_verification_otp(request.phone_number, request.phone_country_code, db)
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {"message": "OTP sent to your phone"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send phone OTP: {str(e)}")

@password_auth.post("/verify-otp", summary="Verify OTP for email or phone", tags=["Verification"])
async def verify_otp(request: OTPVerificationRequest, db: AsyncSession = Depends(db)):
    """Verify the OTP for email or phone number"""
    try:
        # is_valid = otp_service.verify_otp(request.identifier, request.otp)
        if request.type not in ['email', 'phone']:
            return {"message": "Invalid verification type", "status": "error"}
        
        is_valid = await otp_service.verify_otp(request.identifier, request.otp, request.type, db)

        
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
        
        return {"message": "Verification successful", "status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

@password_auth.get("/verification-status", summary="Get verification status", tags=["Verification"])
async def get_verification_status(email: Optional[str] = None, phone: Optional[str] = None, db_session: AsyncSession = Depends(db)):
    """
    Get the verification status for an email and/or phone number
    
    Args:
        email: Email address to check
        phone: Phone number to check
        db_session: Database session
        
    Returns:
        VerificationStatus object
    """
    try:
        status = VerificationStatus()
        
        if email:
            status.email_verified = await otp_service.is_verified(email, 'email', db_session)
            
        if phone:
            status.phone_verified = await otp_service.is_verified(phone, 'phone', db_session)
            
        return status
    except Exception as e:
        logger.exception(f"Exception in get_verification_status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get verification status: {str(e)}")

@password_auth.post("/resend-otp", summary="Resend OTP for verification", tags=["Verification"])
async def resend_otp(
    identifier: str, 
    type: str, 
    db_session: AsyncSession = Depends(db)
):
    """
    Resend OTP for verification
    
    Args:
        identifier: Email or phone number
        type: 'email' or 'phone'
        db_session: Database session
        
    Returns:
        Dict with status and message
    """
    try:
        if type not in ['email', 'phone']:
            raise HTTPException(status_code=400, detail="Invalid verification type")
        
        if type == 'email':
            result = await send_email_verification_otp(identifier, db_session)
        else:
            result = await send_phone_verification_otp(identifier, db_session)
            
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to resend OTP"))
            
        return {"message": f"OTP resent to your {type}", "status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Exception in resend_otp: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to resend OTP: {str(e)}")

@password_auth.post("/link-to-user", summary="Link verified identifiers to user", tags=["Verification"])
async def link_to_user(
    user_id: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    db_session: AsyncSession = Depends(db)
):
    """
    Link verified email and/or phone to a user
    
    Args:
        user_id: User ID to link to
        email: Email address to link
        phone: Phone number to link
        db_session: Database session
        
    Returns:
        Dict with status and message
    """
    try:
        results = {}
        
        if email:
            email_linked = await otp_service.link_to_user(email, 'email', user_id, db_session)
            results["email"] = "linked" if email_linked else "not verified"
            
        if phone:
            phone_linked = await otp_service.link_to_user(phone, 'phone', user_id, db_session)
            results["phone"] = "linked" if phone_linked else "not verified"
            
        return {
            "status": "success",
            "message": "Identifiers linked to user",
            "results": results
        }
    except Exception as e:
        logger.exception(f"Exception in link_to_user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to link identifiers to user: {str(e)}")


@password_auth.delete("/clear-verification", summary="Clear verification data", tags=["Verification"])
async def clear_verification(
    identifier: str,
    type: str,
    db_session: AsyncSession = Depends(db)
):
    """
    Clear verification data for an identifier
    
    Args:
        identifier: Email or phone number
        type: 'email' or 'phone'
        db_session: Database session
        
    Returns:
        Dict with status and message
    """
    try:
        if type not in ['email', 'phone']:
            raise HTTPException(status_code=400, detail="Invalid verification type")
                
        # Delete the verified identifier record
        query = select(VerifiedIdentifier).where(
            VerifiedIdentifier.identifier == identifier,
            VerifiedIdentifier.type == type
        )
        result = await db_session.execute(query)
        verified_identifier = result.scalar_one_or_none()

        if verified_identifier:
            await db_session.delete(verified_identifier)
            await db_session.commit()
            return {"message": f"{type.capitalize()} verification cleared", "status": "success"}
        else:
            return {"message": f"No verification found for this {type}", "status": "info"}

    except Exception as e:
        db_session.rollback()
        logger.exception(f"Exception in clear_verification: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear verification: {str(e)}")
    




# Add these new models
class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    password: str


@password_auth.post("/request-password-reset", summary="Request password reset email", tags=["Auth"])
async def request_password_reset(request: PasswordResetRequest, db: AsyncSession = Depends(db)):
    """
    Send a password reset email to the user
    """
    # Check if user exists
    user = await get_user(db, request.email)
    if not user:
        # Don't reveal if user exists or not for security reasons
        return {"message": "If your email is registered, you will receive a password reset link"}
    
    # Generate a secure token
    reset_token = otp_service.generate_password_reset_token(user.user_uuid)
    
    # Send email with reset token
    result = send_password_reset_email(request.email, reset_token)
    
    if result.get("status") == "error":
        logger.error(f"Failed to send password reset email: {result.get('message')}")
        raise HTTPException(status_code=500, detail="Failed to send password reset email")
    
    return {"message": "If your email is registered, you will receive a password reset link"}



@password_auth.post("/reset-password", summary="Reset password with token", tags=["Auth"])
async def reset_password(reset_data: PasswordResetConfirm, db: AsyncSession = Depends(db)):
    """
    Reset user password using the token received via email
    """
    try:
        # Verify token and get user_id
        user_id = otp_service.verify_password_reset_token(reset_data.token)
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        
        # Find user by UUID
        # user = db.query(User).filter(User.user_uuid == user_id).first()
        user = await get_user_by_uuid(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update password
        hashed_password = get_password_hash(reset_data.password)
        user.password_hash = hashed_password
        await db.commit()
        
        return {"message": "Password has been reset successfully"}
    
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    except Exception as e:
        logger.exception(f"Password reset failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Password reset failed: {str(e)}")
