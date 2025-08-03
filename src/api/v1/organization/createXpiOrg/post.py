from fastapi import HTTPException, Depends, Request, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Literal
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import logging
from uuid import uuid4
from src.datamodel.database.userauth.AuthenticationTables import Entity,Address,User,Role,UserEntityRoleMap
from src.core.authentication.authentication import get_current_user
from sqlalchemy.exc import IntegrityError
from src.datamodel.datavalidation.apiconfig import ApiConfig  
from src.core.database.dbs.getdb import postresql as db
from src.services.permit.permit_service import PermitService


logger = logging.getLogger(__name__)
permit_service = PermitService()


class EntityCreate(BaseModel):
    entity_type: str  # "parent" or "organization"
    name: str
    description: Optional[str] = None  # Used for organizations
    headcount: Optional[int] = None  # Used for parents
    domain: Optional[str] = None  # Used for parents
    parent_uuid: Optional[str] = None  # Reference to parent entity
    address_id: Optional[int] = None  # Foreign key reference
    created_by: Optional[str] = None
    updated_by: Optional[str] = None  

def api_config():
    config = {
        "path": "",
        "status_code": 201,
        "tags": ["Organization"],
        "summary": "Create and save organization for xpi",
        "response_model": dict,
        "description": "This API endpoint creates a new Entity and saves it in the database.",
        "response_description": "Details of the created entity.",
        "deprecated": False,
    }
    return ApiConfig(**config)

async def create_entity(entity_data: EntityCreate, db: AsyncSession):

    try:
        # create organization in permit.io
        new_tenant = await permit_service.get_digital_signage_org()

        entity_uuid = str(new_tenant.id)

        # check for already present entity

        # entity = db.query(Entity).filter(Entity.entity_uuid == entity_uuid).first()
        query = select(Entity).where(Entity.entity_uuid == entity_uuid)
        result = await db.execute(query)
        entity = result.scalar_one_or_none()

        if entity:
            raise HTTPException(status_code=400, detail="Entity already exists")
        
        # Create the new entity
        new_entity = Entity(
            entity_uuid=entity_uuid,
            entity_key=new_tenant.key,
            entity_type=entity_data.entity_type,
            name=new_tenant.name,
            description=new_tenant.description,
            headcount=entity_data.headcount,
            domain=entity_data.domain,
            is_active=True,
            parent_uuid=entity_data.parent_uuid,
            address_id=entity_data.address_id,
            created_by=entity_data.created_by,
            updated_by=entity_data.updated_by,
            created_on=datetime.utcnow(),
            updated_on=datetime.utcnow()
        )
        db.add(new_entity)
        await db.commit()
        await db.refresh(new_entity)

        # # Fetch the "superadmin" role
        # admin_role = db.query(Role).filter_by(role_name="superadmin" ).first()
        # if not admin_role:
        #     raise HTTPException(status_code=400, detail="Superadmin role does not exist")

        # Create a mapping in UserEntityRoleMap
        role_mapping = UserEntityRoleMap(
            user_uuid=None,  # The user creating the entity
            role_id= 4,        # The "xpi-team" role
            entity_uuid=entity_uuid, # The newly created entity
        )
        db.add(role_mapping)
        await db.commit()

        return {
            "message": "Entity created successfully and role mapped",
            "entity_uuid": new_entity.entity_uuid,
            "name": new_entity.name,
        }
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Integrity error: Possibly duplicate or invalid foreign key reference")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

async def main(
    entity_data: EntityCreate, 
    db: AsyncSession = Depends(db), 
    # current_user: User = Depends(get_current_user)  # Get the current user
):
    return await create_entity(entity_data, db)
