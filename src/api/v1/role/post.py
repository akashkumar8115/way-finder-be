from fastapi import HTTPException, Depends, Request, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Literal
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import logging
from uuid import uuid4
from src.datamodel.database.userauth.AuthenticationTables import Entity,Address,User,Role
from src.core.authentication.authentication import get_current_user
from sqlalchemy.exc import IntegrityError
from src.datamodel.datavalidation.apiconfig import ApiConfig  
from src.core.database.dbs.getdb import postresql as db
from src.services.permit.permit_service import PermitService


logger = logging.getLogger(__name__)
permit_service = PermitService()


class RoleCreate(BaseModel):
    role_name: str
    description: Optional[str] = None
    is_active: bool = True
    created_by: Optional[str] = None
    updated_by: Optional[str] = None  

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

async def create_role(role: RoleCreate, db):
    # Check if role_name already exists
    # existing_role = db.query(Role).filter(Role.role_name == role.role_name).first()
    query = select(Role).where(Role.role_name == role.role_name)
    result = await db.execute(query)
    existing_role = result.scalar_one_or_none()

    # total_roles = db.query(Role).count()
    total_roles_query = select(Role)
    total_roles_result = await db.execute(total_roles_query)
    total_roles = len(total_roles_result.scalars().all())

    if existing_role:
        raise HTTPException(status_code=400, detail="Role with this name already exists")
    
    # Create new role with ID as total_roles + 1
    new_role_id = total_roles + 1

    # Create new role
    new_role = Role(
        role_id=new_role_id,
        role_name=role.role_name,
        description=role.description,
        is_active=role.is_active,
        created_by=role.created_by,
        updated_by=role.updated_by
    )

    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)  # Refresh to get the auto-generated role_id and timestamps

    # Create role in Permit.io
    # role_key = f"role_{new_role.role_id}"
    role_key = new_role.role_id
    name = new_role.role_name
    description = new_role.description

    await permit_service.create_role(role_key, name, description)
    
    # db.add(new_role)
    # db.commit()
    # db.refresh(new_role)  # Refresh to get the auto-generated role_id and timestamps
    return {
        "role_id": new_role.role_id,
        "role_name": new_role.role_name,
        "description": new_role.description,
    }

async def main(
    role_data: RoleCreate, 
    db: AsyncSession = Depends(db),
):
    return await create_role(role_data, db)

