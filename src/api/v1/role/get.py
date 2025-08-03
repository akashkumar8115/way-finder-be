from fastapi import HTTPException, Depends, Request, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Literal
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging
from uuid import uuid4
from src.datamodel.database.userauth.AuthenticationTables import User, Role
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
        "tags": ["Roles"],
        "summary": "Create and save a new role",
        "response_model": dict,
        "description": "This API endpoint creates a new role and saves it in the database.",
        "response_description": "Details of the created role.",
        "deprecated": False,
    }
    return ApiConfig(**config)


async def get_all_roles(db: AsyncSession) -> Dict[str, List[dict]]:
    """
    Retrieve all roles from the database.
    """
    # Create a SELECT statement using SQLAlchemy Core
    query = select(Role)
    
    # Execute the query asynchronously
    result = await db.execute(query)
    
    # Fetch all results
    roles = result.scalars().all()
    
    if not roles:
        raise HTTPException(status_code=404, detail="No roles found")

    return {"roles": jsonable_encoder(roles)}  # Wrap the list inside a dictionary


async def main(db: AsyncSession = Depends(db)):
    return await get_all_roles(db=db)
