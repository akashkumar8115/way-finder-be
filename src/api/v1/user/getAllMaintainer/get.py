from fastapi import HTTPException, Depends, Request, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Literal
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import logging
from uuid import uuid4
from src.datamodel.database.userauth.AuthenticationTables import Entity,User,Role,UserEntityRoleMap
from src.core.authentication.authentication import get_current_user , get_token_payload
from sqlalchemy.exc import IntegrityError
from src.datamodel.datavalidation.apiconfig import ApiConfig  
from src.core.database.dbs.getdb import postresql as db
from fastapi.encoders import jsonable_encoder
logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 201,
        "tags": ["User"],
        "summary": "Create and save maitainer (user) data",
        "response_model": dict,
        "description": "This API endpoint creates a new user and saves it in the database.",
        "response_description": "Details of the created user.",
        "deprecated": False,
    }
    return ApiConfig(**config)


async def get_all_entities_with_roles(db: AsyncSession, current_user: User) -> Dict:
    try:
        # Step 1: Get Admin entities
        admin_query = select(UserEntityRoleMap).where(
            UserEntityRoleMap.user_uuid == current_user.user_uuid,
            UserEntityRoleMap.role_id == 2
        )
        admin_entities_result = await db.execute(admin_query)
        admin_entities = admin_entities_result.scalars().all()

        if not admin_entities:
            return {"message": "User is not an Admin of any entity"}

        admin_entity_uuids = [mapping.entity_uuid for mapping in admin_entities]
        entity_list = []

        for entity_uuid in admin_entity_uuids:
            entity_result = await db.execute(
                select(Entity).where(Entity.entity_uuid == entity_uuid)
            )
            entity = entity_result.scalar_one_or_none()
            if not entity:
                continue

            # Maintainers query
            maintainer_query = (
                select(UserEntityRoleMap, User, Role)
                .join(User, User.user_uuid == UserEntityRoleMap.user_uuid)
                .join(Role, Role.role_id == UserEntityRoleMap.role_id)
                .where(
                    UserEntityRoleMap.entity_uuid == entity_uuid,
                    UserEntityRoleMap.role_id == 3
                )
            )
            maintainer_result = await db.execute(maintainer_query)
            maintainer_roles = maintainer_result.all()

            maintainer_users = [
                {
                    "user_uuid": user.user_uuid,
                    "name": f"{user.first_name} {user.last_name}",
                    "username": user.username,
                    "email": user.email,
                    "role_name": role.role_name
                }
                for mapping, user, role in maintainer_roles
            ]

            entity_list.append({
                "entity_uuid": entity.entity_uuid,
                "entity_name": entity.name,
                "entity_key": entity.entity_key,
                "entity_type": entity.entity_type,
                "description": entity.description,
                "maintainer_users": maintainer_users
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