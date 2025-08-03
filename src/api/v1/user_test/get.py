import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends, Security, Request, status
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.database.dbs.getdb import postresql as db
from src.core.database.curd.user import get_user
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.authentication.authentication import get_current_user, User, get_token_payload

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Users"],
        "summary": "Get User Details",
        "response_model": dict,
        "description": "Fetch user details by username and provider",
        "response_description": "Returns user details if found",
        "deprecated": False,
    }
    return ApiConfig(**config)

async def main(
    request: Request,
    db: AsyncSession = Depends(db)
):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing Token"
        )

    # Extract token from Bearer format
    try:
        token_type, token = auth_header.split()
        if token_type.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )

    try:
        # Validate token and get user
        token_payload = get_token_payload(token)  # Ensure this function exists
        user = await get_current_user(db=db, token_payload=token_payload)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        return {
            "username": user.username,
            "user_uuid": user.user_uuid,
            "email": user.email,
            "first_name": user.first_name,
            "middle_name": user.middle_name,
            "last_name": user.last_name,
            "provider": user.provider,
            "phone_number": user.phone_number,
            "phone_country_code": user.phone_country_code,
            "is_active": user.is_active,
            "created_on": user.created_on,
            "profile_pic": user.profile_pic
        }

    except Exception as e:
        logger.error(f"Error fetching user details: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
