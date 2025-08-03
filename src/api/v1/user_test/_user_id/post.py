# import logging
# from sqlalchemy.orm import Session
# from fastapi import HTTPException, Depends
# from src.datamodel.datavalidation.apiconfig import ApiConfig
# from src.core.database.dbs.getdb import postresql as db
# from src.datamodel.datavalidation.user import UserUpdate
# from src.core.database.curd.user import get_user, update_user
# from src.core.authentication.authentication import get_current_user
# from typing import Annotated

# logger = logging.getLogger(__name__)

# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Users"],
#         "summary": "Update User Details",
#         "response_model": dict,
#         "description": "Update existing user details",
#         "response_description": "Returns updated user details",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)


# async def main(
#     user: UserUpdate,
#     current_user: Annotated[dict, Depends(get_current_user)],
#     db: Session = Depends(db)
# ):
#     try:
#         if not current_user:
#             raise HTTPException(status_code=401, detail="Authentication required")

#         # Only allow users to update their own profile
#         if user.username != current_user["username"] or user.provider != current_user["provider"]:
#             raise HTTPException(status_code=403, detail="Cannot update other user's profile")

#         # Validate if user exists
#         existing_user = get_user(db=db, username=user.username, provider=user.provider)
#         if not existing_user:
#             raise HTTPException(status_code=404, detail="User not found")
        
#         # Validate phone number if provided
#         if user.phone_number and (not user.phone_number.isdigit() or len(user.phone_number) != 10):
#             raise HTTPException(status_code=400, detail="Invalid phone number format")
        
#         # Update user details
#         updated_user = update_user(db=db, user=user)
        
#         # Return updated user details
#         user_details = get_user(db=db, username=user.username, provider=user.provider)
#         return {
#             "username": user_details.username,
#             "email": user_details.email,
#             "first_name": user_details.first_name,
#             "middle_name": user_details.middle_name,
#             "last_name": user_details.last_name,
#             "provider": user_details.provider,
#             "phone_number": user_details.phone_number,
#             "phone_country_code": user_details.phone_country_code,
#             "profile_pic": user_details.profile_pic,
#             "message": "User updated successfully"
#         }
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         logger.error(f"Error updating user: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))









import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, Depends
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.database.dbs.getdb import postresql as db
from src.datamodel.datavalidation.user import UserUpdate
from src.core.database.curd.user import get_user, update_user
from src.core.authentication.authentication import get_current_user
from src.datamodel.database.userauth.AuthenticationTables import User
from typing import Annotated
from sqlalchemy import select

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Users"],
        "summary": "Update User Details",
        "response_model": dict,
        "description": "Update existing user details",
        "response_description": "Returns updated user details",
        "deprecated": False,
    }
    return ApiConfig(**config)

async def main(
    user: UserUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(db)
):
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Only allow users to update their own profile
        if user.username != current_user["username"] or user.provider != current_user["provider"]:
            raise HTTPException(status_code=403, detail="Cannot update other user's profile")

        # Validate if user exists
        query = select(User).where(
            User.username == user.username,
            User.provider == user.provider
        )
        result = await db.execute(query)
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate phone number if provided
        if user.phone_number and (not user.phone_number.isdigit() or len(user.phone_number) != 10):
            raise HTTPException(status_code=400, detail="Invalid phone number format")
        
        # Update user details
        updated_user = await update_user(db=db, user=user)
        
        # Get updated user details
        query = select(User).where(
            User.username == user.username,
            User.provider == user.provider
        )
        result = await db.execute(query)
        user_details = result.scalar_one_or_none()

        return {
            "username": user_details.username,
            "email": user_details.email,
            "first_name": user_details.first_name,
            "middle_name": user_details.middle_name,
            "last_name": user_details.last_name,
            "provider": user_details.provider,
            "phone_number": user_details.phone_number,
            "phone_country_code": user_details.phone_country_code,
            "profile_pic": user_details.profile_pic,
            "message": "User updated successfully"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
