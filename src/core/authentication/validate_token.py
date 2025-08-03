from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy.orm import Session
import logging

from src.core.authentication.authentication import User, get_current_user

# initializing logging
logger = logging.getLogger(__name__)

validate_token = APIRouter()

@validate_token.get("/validate-token", tags=["Auth"])
# async def validate_usertoken(current_user: Annotated[User, Depends(get_current_user)]):
async def validate_usertoken(current_user: Annotated[User, Depends(get_current_user)]):
    try:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if current_user.inactive_date != None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
            )

        return {"user": current_user}
    except HTTPException as e:
        logger.error(f"HTTPException: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )