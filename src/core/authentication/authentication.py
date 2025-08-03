from passlib.context import CryptContext
from jose import JWTError, jwt
from jose.constants import ALGORITHMS
from fastapi.security import OAuth2PasswordBearer, APIKeyCookie
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import uuid
import logging
from typing import Annotated, Optional
from src.core.authentication.cred_load import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, SESSION_COOKIE_NAME
from src.datamodel.database.userauth.AuthenticationTables import User, Entity, Role, UserEntityRoleMap
from src.core.database.dbs.getdb import postresql as db
from src.core.database.curd.user import get_user, add_user, DuplicateError
from src.datamodel.datavalidation.user import UserDetails
from src.services.otp_generation.otp_service import OTPService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


# initializing logging
logger = logging.getLogger(__name__)

otp_service = OTPService()

COOKIE = APIKeyCookie(name=SESSION_COOKIE_NAME, auto_error=False, scheme_name=SESSION_COOKIE_NAME)

class BearAuthException(Exception):
    pass


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)


async def authenticate_user(db: AsyncSession, username: str, password:str, provider: str, auth_flow: str):
    user = await get_user(db, username, provider)
    if not user:
        if auth_flow == 'login':
            raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        return False
    elif user and auth_flow == 'thrid_party':
        return user
    elif not verify_password(password, user.password_hash) and auth_flow == 'login':
        print("Wrong password")
        raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    elif user and auth_flow == 'signup':
        raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User already exisits",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    else:
        return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Create a JWT access token with the provided data and expiration time.
    
    Args:
        data: Dictionary containing user data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_token_payload(session_token: str = Depends(COOKIE)):
    try:
        if not session_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session token is missing"
            )
        # payload = jwt.decode(session_token, SECRET_KEY, algorithms=[ALGORITHMS.HS256])
        payload = jwt.decode(session_token, SECRET_KEY, algorithms=[ALGORITHM])

        username: str = payload.get("username")
        provider: str = payload.get("provider")
        role_id: str = payload.get("role_id")
        user_uuid: str = payload.get("user_uuid")
        first_name: str = payload.get("first_name")
        last_name: str = payload.get("last_name")
        entity_uuid: str = payload.get("entity_uuid")
        entity_key: str = payload.get("entity_key")

        if username is None or provider is None:
            raise BearAuthException("Token could not be validated")
        return {
            "username": username,
            "provider": provider,
            "role_id": role_id,
            "user_uuid": user_uuid,
            "first_name": first_name,
            "last_name": last_name,
            "entity_uuid": entity_uuid,
            "entity_key": entity_key
        }
    except JWTError as e:
        raise BearAuthException(f"Token could not be validated: {e}")


async def get_current_user(db: AsyncSession = Depends(db), token_payload: dict = Depends(get_token_payload)):
    try:
        # userdata = get_token_payload(session_token)
        username = token_payload.get('username')
        provider = token_payload.get('provider')
    except BearAuthException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate bearer token: {e}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the session token: {str(e)}"
        )
    if not username or not provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token payload is missing required information"
        )
    user = await get_user(db, username=username, provider=provider)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


async def get_user_by_uuid(db: AsyncSession, user_id: str):
    # return db.query(User).filter(User.user_uuid == user_id).first()
    stmt = select(User).where(User.user_uuid == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first() 

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user



async def login_flow(user: object, db: AsyncSession, auth_flow: str):
    try:
        username = user.email if not hasattr(user, 'username') else user.username
        password = None if not hasattr(user, 'password') else user.password
        entity_uuid = None
        entity_key = None
        
        user_stored = await authenticate_user(db=db, username=username, password=password, provider=user.provider, auth_flow=auth_flow)
        if user_stored and auth_flow == 'login':
            # Find entity_uuid
            query = (
                select(Entity)
                .join(UserEntityRoleMap, Entity.entity_uuid == UserEntityRoleMap.entity_uuid)
                .where(UserEntityRoleMap.user_uuid == user_stored.user_uuid)
            )
            result = await db.execute(query)
            entity = result.scalars().first()
            if entity:
                entity_uuid = entity.entity_uuid
                entity_key = entity.entity_key


        if not user_stored:
            middle_name = None if not hasattr(user, 'middle_name') else user.middle_name
            sso_id = None if not hasattr(user, 'id') else user.id
            picture = None if not hasattr(user, 'picture') else user.picture
            role_id = None if not hasattr(user, 'role_id') else user.role_id
           
            user_to_add = UserDetails(
                user_uuid = str(uuid.uuid4()),
                username= username,
                email = user.email,
                first_name=user.first_name,
                middle_name = middle_name,
                last_name = user.last_name,
                provider = user.provider,
                sso_id = sso_id,
                # created_on = datetime.now(timezone.utc),
                created_on = datetime.utcnow(),
                is_active = True,
                profile_pic = picture,
                entity_uuid=user.entity_uuid,
                role_id=user.role_id,
                password = password,
            )
            user_stored = await add_user(db, user_to_add)
        access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))

        # Create token with user details
        token_data = {
            "username": user_stored.username,
            "provider": user.provider,
            "role_id": user_stored.role_id,
            "user_uuid": user_stored.user_uuid,
            "first_name": user_stored.first_name,
            "last_name": user_stored.last_name,
            "entity_uuid": entity_uuid,
            "entity_key": entity_key,
        }
        
        return create_access_token(
            data=token_data,
            expires_delta=access_token_expires
        )                                                     

    

    except HTTPException as http_exc:
        if http_exc.status_code == status.HTTP_409_CONFLICT:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists.")
        else:
            raise http_exc  # Re-raise other HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred. Report this message to support: {e}",
        )
    



async def verify_user_identifiers(email: str, phone_number: Optional[str], db: AsyncSession) -> None:
    """
    Verify that the user's email and phone (if provided) have been verified
    
    Args:
        email: User's email address
        phone_number: User's phone number (optional)
        db: Database session
        
    Raises:
        HTTPException: If email or phone is not verified
    """
    # Check if email is verified
    email_verified = await otp_service.is_verified(email, 'email', db)
    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified. Please verify your email before signing up."
        )
    
    # Check if phone is verified (if provided)
    if phone_number:
        phone_verified = await otp_service.is_verified(phone_number, 'phone', db)
        if not phone_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number not verified. Please verify your phone number before signing up."
            )
    
    # If we get here, all provided identifiers are verified
    logger.info(f"All identifiers verified for email: {email}")



async def link_user_identifiers(user_uuid: str, email: str, phone_number: Optional[str], db: AsyncSession) -> None:
    """
    Link verified identifiers to a user account
    
    Args:
        user_uuid: User's UUID
        email: User's email address
        phone_number: User's phone number (optional)
        db: Database session
    """
    # Link email to user
    email_linked = await otp_service.link_to_user(email, 'email', user_uuid, db)
    if not email_linked:
        logger.warning(f"Failed to link email {email} to user {user_uuid}")
    
    # Link phone to user if provided
    if phone_number:
        phone_linked = await otp_service.link_to_user(phone_number, 'phone', user_uuid, db)
        if not phone_linked:
            logger.warning(f"Failed to link phone {phone_number} to user {user_uuid}")
    
    logger.info(f"Identifiers linked to user {user_uuid}")

