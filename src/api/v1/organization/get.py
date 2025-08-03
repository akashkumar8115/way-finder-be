from fastapi import HTTPException, Depends, Request, status
from pydantic import BaseModel
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import logging
from uuid import uuid4

from src.datamodel.database.userauth.AuthenticationTables import Entity, Role, User, UserEntityRoleMap
from src.core.authentication.authentication import get_current_user, get_token_payload
from src.datamodel.datavalidation.apiconfig import ApiConfig  
from src.core.database.dbs.getdb import postresql as db
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 201,
        "tags": ["Organization"],
        "summary": "Create and save Entity data",
        "response_model": dict,
        "description": "This API endpoint creates a new entity and saves it in the database.",
        "response_description": "Details of the created entity.",
        "deprecated": False,
    }
    return ApiConfig(**config)


async def get_all_entities(db: AsyncSession, current_user: User):
    try:
        # Check if the user is a superadmin
        is_superadmin = False

        query = (
            select(Role)
            .join(UserEntityRoleMap, Role.role_id == UserEntityRoleMap.role_id)
            .where(
                UserEntityRoleMap.user_uuid == current_user.user_uuid,
                Role.role_name.ilike("superadmin")
            )
        )
        result = await db.execute(query)
        superadmin_role = result.scalars().first()

        if superadmin_role:
            is_superadmin = True
        else:
            query_roles = select(UserEntityRoleMap).where(UserEntityRoleMap.user_uuid == current_user.user_uuid)
            result_roles = await db.execute(query_roles)
            user_roles = result_roles.scalars().first()

            if not user_roles:
                raise HTTPException(status_code=403, detail="User has no assigned roles")

        if is_superadmin:
            query_entities = select(Entity).where(Entity.created_by == current_user.user_uuid)
        else:
            query_entities = select(Entity)

        result_entities = await db.execute(query_entities)
        entities = result_entities.scalars().all()

        return {"entities": jsonable_encoder(entities)}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching entities: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def main(request: Request, db: AsyncSession = Depends(db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return {
            "message": "Authorization header is missing or invalid token"
        }

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
        token_payload = get_token_payload(token)
        user = await get_current_user(db=db, token_payload=token_payload)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")

    return await get_all_entities(db=db, current_user=user)

