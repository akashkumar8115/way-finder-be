from fastapi import HTTPException, Depends, Request, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Literal
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging
from uuid import uuid4
from src.datamodel.database.userauth.AuthenticationTables import Entity, Address, User, Role, UserEntityRoleMap
from src.core.authentication.authentication import get_current_user, get_token_payload
from sqlalchemy.exc import IntegrityError
from src.datamodel.datavalidation.apiconfig import ApiConfig  
from src.core.database.dbs.getdb import postresql as db
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 201,
        "tags": ["User"],
        "summary": "Get all users",
        "response_model": dict,
        "description": "This API endpoint retrieves all users associated with the current user's entities.",
        "response_description": "List of users.",
        "deprecated": False,
    }
    return ApiConfig(**config)


async def get_all_entities(db: AsyncSession):
    """
    Get all entity_uuid where the current user has role_id = 1 (Super Admin).
    """
    query = select(UserEntityRoleMap.entity_uuid).where(
        UserEntityRoleMap.role_id.in_([1, 2, 3])  # Admin, Maintainer, Super Admin, etc.
    ).distinct()
    
    result = await db.execute(query)
    entity_uuids = result.all()

    return [entity_uuid[0] for entity_uuid in entity_uuids]


async def get_all_entities_with_roles(db: AsyncSession, current_user: User):
    """
    Fetch all entities where the user is a Super Admin, along with categorized Admins & Maintainers.
    """
    try:
        all_entities = await get_all_entities(db)

        if not all_entities:
            return {"message": "User is not a Super Admin of any entity"}

        entity_list = []
        for entity_uuid in all_entities:
            # Get entity details
            entity_query = select(Entity).where(Entity.entity_uuid == entity_uuid)
            entity_result = await db.execute(entity_query)
            entity = entity_result.scalar_one_or_none()
            
            if not entity:
                continue

            # Fetch users with roles for this entity
            user_roles_query = (
                select(UserEntityRoleMap, User, Role)
                .join(User, User.user_uuid == UserEntityRoleMap.user_uuid)
                .join(Role, Role.role_id == UserEntityRoleMap.role_id)
                .where(
                    UserEntityRoleMap.entity_uuid == entity_uuid,
                    UserEntityRoleMap.role_id.in_([1, 2, 3])  # Admin & Maintainer
                )
            )
            user_roles_result = await db.execute(user_roles_query)
            user_roles = user_roles_result.all()
            
            superadmin_user = []
            admin_users = []
            maintainer_users = []

            for mapping, user, role in user_roles:
                user_data = {
                    "user_uuid": user.user_uuid,
                    "name": user.first_name + " " + user.last_name,
                    "username": user.username,
                    "email": user.email,
                    "role_name": role.role_name  # Ensure correct role name is returned
                }

                if role.role_id == 2:
                    admin_users.append(user_data)
                elif role.role_id == 3:
                    maintainer_users.append(user_data)
                elif role.role_id == 1:
                    superadmin_user.append(user_data)
                    
            entity_list.append({
                "entity_uuid": entity.entity_uuid,
                "entity_name": entity.name,
                "admin_users": admin_users,
                "maintainer_users": maintainer_users,
                "superadmin_user": superadmin_user
            })

        return {"entities": entity_list}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching entities with roles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def main(request: Request, db: AsyncSession = Depends(db)):
    """
    Authenticate the user and fetch all entities they have created.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return{
            "messege": "Authorization header is missing or invalid token"
        }

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
    try:
        token_payload = get_token_payload(token)  # Ensure this function is implemented
        user = await get_current_user(db=db, token_payload=token_payload)
    
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")

    return await get_all_entities_with_roles(db=db, current_user=user)


