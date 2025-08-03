from fastapi import HTTPException, Depends, Request, status
import logging
from bson import ObjectId
import asyncio
from typing import Dict, List
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.authentication.authentication import get_current_user, get_token_payload
from src.datamodel.database.userauth.AuthenticationTables import Entity, Role, User, UserEntityRoleMap
from sqlalchemy.exc import IntegrityError
from src.core.database.dbs.getdb import postresql as db
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.permit.permit_service import PermitService
from sqlalchemy import select

logger = logging.getLogger(__name__)
permit_service = PermitService()

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["User"],
        "summary": "Delete a User",
        "response_model": None,
        "description": "Delete a user",
        "response_description": "Deletion status with update details",
        "deprecated": False,
    }
    return ApiConfig(**config)

async def delete_user(user_id: str, db: AsyncSession, current_user: User):
    try:
        # Find the target user using user_uuid
        query = select(User).where(User.user_uuid == user_id)
        result = await db.execute(query)
        user_to_delete = result.scalar_one_or_none()

        if not user_to_delete:
            raise HTTPException(status_code=404, detail="User not found")

        # Get roles of current user and user to be deleted
        current_role_query = select(Role).where(Role.role_id == int(current_user.role_id))
        current_role_result = await db.execute(current_role_query)
        current_user_role = current_role_result.scalar_one_or_none()
        
        target_role_query = select(Role).where(Role.role_id == int(user_to_delete.role_id))
        target_role_result = await db.execute(target_role_query)
        target_user_role = target_role_result.scalar_one_or_none()

        if not current_user_role or not target_user_role:
            raise HTTPException(status_code=400, detail="Unable to resolve roles")

        if current_user.role_id == 4:
            pass
        # Authorization logic
        elif current_user.role_id == 1:
            # Super admin can delete Admin (2) and Maintainer (3)
            if target_user_role.role_id not in [2, 3]:
                raise HTTPException(status_code=403, detail="Super admin can't delete this user type")
        elif current_user.role_id == 2:
            # Admin can only delete Maintainer (3)
            if target_user_role.role_id != 3:
                raise HTTPException(status_code=403, detail="Admin can only delete Maintainers")
        else:
            raise HTTPException(status_code=403, detail="You don't have permission to delete users")

        # Find the entity key from UserEntityRoleMap
        map_query = select(UserEntityRoleMap).where(
            UserEntityRoleMap.user_uuid == user_to_delete.user_uuid
        )
        map_result = await db.execute(map_query)
        user_entity_map = map_result.scalar_one_or_none()
        
        if not user_entity_map:
            logger.warning(f"No entity mapping found for user {user_id}")
            entity_key = None
        else:
            # Get the entity details
            entity_query = select(Entity).where(
                Entity.entity_uuid == user_entity_map.entity_uuid
            )
            entity_result = await db.execute(entity_query)
            entity = entity_result.scalar_one_or_none()
            
            if not entity:
                logger.warning(f"Entity not found for user {user_id}")
                entity_key = None
            else:
                entity_key = entity.entity_key

        # Delete from UserEntityRoleMap
        delete_query = select(UserEntityRoleMap).where(
            UserEntityRoleMap.user_uuid == user_to_delete.user_uuid
        )
        delete_result = await db.execute(delete_query)
        mappings_to_delete = delete_result.scalars().all()
        
        for mapping in mappings_to_delete:
            await db.delete(mapping)

        await db.commit()    

        # Delete from Permit.io if entity_key was found
        if entity_key:
            await permit_service.remove_user_from_permit(
                user_to_delete.email, 
                entity_key, 
                target_user_role.role_id
            )

        # Delete the user
        await db.delete(user_to_delete)
        await db.commit()

        return {
            "message": f"User with ID {user_id} deleted successfully"
        }

    except HTTPException as e:
        await db.rollback()
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

async def main(
    _id: str,
    request: Request,
    db: AsyncSession = Depends(db)
):
    """
    Main function to handle user deletion
    """
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

    # Validate token and get user
    token_payload = get_token_payload(token)
    user = await get_current_user(db=db, token_payload=token_payload)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return await delete_user(_id, db, user)


