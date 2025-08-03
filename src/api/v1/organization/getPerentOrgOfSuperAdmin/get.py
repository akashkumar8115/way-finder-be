from fastapi import HTTPException, Depends, Request, status
from pydantic import BaseModel
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime
import logging
from uuid import uuid4

from src.datamodel.database.userauth.AuthenticationTables import Entity, Address, User, Role, UserEntityRoleMap
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
        "response_description": "Details of the Entity.",
        "deprecated": False,
    }
    return ApiConfig(**config)


async def get_Org_Of_Superadmin(db: AsyncSession, entity_uuid: str) -> Dict[str, List[dict]]:
    try:
        query = select(Entity).where(
            and_(
                Entity.entity_uuid == entity_uuid,
                Entity.parent_uuid.is_(None)
            )
        )
        result = await db.execute(query)
        entities = result.scalars().all()
        return {"parentOrg": jsonable_encoder(entities)}

    except Exception as e:
        logger.error(f"Error fetching root parent entities: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching entities")


async def main(request: Request, db: AsyncSession = Depends(db)):
    """
    Authenticate the user and fetch their root parent organization entity.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return {
            "message": "Authorization header is missing or invalid token"
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

    # Fetch role mapping to get the entity UUID
    query = select(UserEntityRoleMap).where(
        and_(
            UserEntityRoleMap.user_uuid == user.user_uuid,
            UserEntityRoleMap.role_id == 1  # assuming role_id 1 is superadmin
        )
    )
    result = await db.execute(query)
    user_org_role = result.scalars().first()

    if not user_org_role:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    entity_uuid = user_org_role.entity_uuid
    return await get_Org_Of_Superadmin(db=db, entity_uuid=entity_uuid)
