from fastapi import HTTPException, Depends, Request, status
from pydantic import BaseModel
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
import logging

from src.datamodel.database.userauth.AuthenticationTables import Entity, User, Role, UserEntityRoleMap
from src.core.authentication.authentication import get_current_user, get_token_payload
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.database.dbs.getdb import postresql as db
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["User"],
        "summary": "Get entities managed by Super Admin",
        "response_model": dict,
        "description": "This API returns all entities for which the authenticated user is a Super Admin, along with Admins and Maintainers categorized.",
        "response_description": "Entities with Admin and Maintainer user lists.",
        "deprecated": False,
    }
    return ApiConfig(**config)


async def get_superadmin_entity_uuids(db: AsyncSession, user_uuid: str) -> List[str]:
    try:
        query = select(UserEntityRoleMap.entity_uuid).where(
            UserEntityRoleMap.user_uuid == user_uuid,
            UserEntityRoleMap.role_id == 1
        ).distinct()

        result = await db.execute(query)
        return [row[0] for row in result.all()]
    except Exception as e:
        logger.error(f"Failed to fetch Super Admin entities: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch Super Admin entities.")


async def get_all_entities_with_roles(db: AsyncSession, current_user: User):
    try:
        superadmin_entity_uuids = await get_superadmin_entity_uuids(db, current_user.user_uuid)

        if not superadmin_entity_uuids:
            return {"message": "User is not a Super Admin of any entity"}

        entities_data = []

        for entity_uuid in superadmin_entity_uuids:
            entity_query = await db.execute(select(Entity).where(Entity.entity_uuid == entity_uuid))
            entity = entity_query.scalars().first()

            if not entity:
                continue

            user_roles_query = await db.execute(
                select(UserEntityRoleMap, User, Role)
                .join(User, User.user_uuid == UserEntityRoleMap.user_uuid)
                .join(Role, Role.role_id == UserEntityRoleMap.role_id)
                .where(
                    UserEntityRoleMap.entity_uuid == entity_uuid,
                    UserEntityRoleMap.role_id.in_([2, 3])
                )
            )

            admin_users, maintainer_users = [], []

            for mapping, user, role in user_roles_query.all():
                user_info = {
                    "user_uuid": user.user_uuid,
                    "name": f"{user.first_name} {user.last_name}",
                    "username": user.username,
                    "email": user.email,
                    "role_name": role.role_name
                }

                if role.role_id == 2:
                    admin_users.append(user_info)
                elif role.role_id == 3:
                    maintainer_users.append(user_info)

            entities_data.append({
                "entity_uuid": entity.entity_uuid,
                "entity_name": entity.name,
                "admin_users": admin_users,
                "maintainer_users": maintainer_users
            })

        return {"entities": entities_data}

    except Exception as e:
        logger.error(f"Error fetching entities with roles: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def main(request: Request, db: AsyncSession = Depends(db)):
    """
    Authenticate the user and fetch all entities where the user is a Super Admin.
    """
    logger.info("Starting authentication process...")
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    try:
        token_type, token = auth_header.split()
        if token_type.lower() != "bearer":
            raise ValueError("Invalid token type")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    try:
        token_payload = get_token_payload(token)
        user = await get_current_user(db=db, token_payload=token_payload)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")

    return await get_all_entities_with_roles(db=db, current_user=user)


