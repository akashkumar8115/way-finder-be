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
from sqlalchemy import and_, select
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

async def get_all_root_parents(db: AsyncSession):
    try:
        # Create a SELECT statement using SQLAlchemy Core
        query = select(Entity).where(
            and_(
                Entity.parent_uuid.is_(None),      # parent_uuid is NULL
                Entity.entity_type == "parent"      # entity_type is 'parent'
            )
        )
        
        # Execute the query asynchronously
        result = await db.execute(query)
        
        # Fetch all results
        entities = result.scalars().all()

        return {"entities": jsonable_encoder(entities)}
    except Exception as e:
        logger.error(f"Error fetching root parent entities: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching entities")

async def main(request: Request, db: AsyncSession = Depends(db)):
    """
    # Authenticate the user and fetch all entities they have created.
    # """
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
        token_payload = get_token_payload(token)
        # Make sure get_current_user is also async
        user = await get_current_user(db=db, token_payload=token_payload)
    
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")

    return await get_all_root_parents(db=db)




