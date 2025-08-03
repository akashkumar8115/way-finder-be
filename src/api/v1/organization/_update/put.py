from fastapi import HTTPException, Depends, Request, status
import logging
from bson import ObjectId
import asyncio
from typing import Dict, List
from typing import Optional
from pydantic import BaseModel
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.authentication.authentication import get_current_user, get_token_payload
from src.datamodel.database.userauth.AuthenticationTables import Entity, Role, User, UserEntityRoleMap
from sqlalchemy.exc import IntegrityError
from src.core.database.dbs.getdb import postresql as db
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from src.services.permit.permit_service import PermitService
from sqlalchemy import select

logger = logging.getLogger(__name__)
permit_service = PermitService()

class UpdateOrganizationRequest(BaseModel):
    entity_type: Optional[str] = None  # "parent" or "organization"
    name: Optional[str] = None
    description: Optional[str] = None  # Used for organizations
    headcount: Optional[int] = None  # Used for parents
    domain: Optional[str] = None  # Used for parents
    parent_uuid: Optional[str] = None  # Reference to parent entity
    address_id: Optional[int] = None  # Foreign key reference

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Organization"],
        "summary": "Update Entity data",
        "response_model": None,
        "description": "This API endpoint updates an existing entity in the database.",
        "response_description": "Details of the updated entity.",
        "deprecated": False,
    }
    return ApiConfig(**config)

async def update_organization(entity_uuid: str, update_data: UpdateOrganizationRequest, db: AsyncSession, current_user: User):
    try:
        # Check if the current user has the "superadmin" or "xpiteam" role
        role_query = select(Role).where(Role.role_id == current_user.role_id)
        role_result = await db.execute(role_query)
        user_role = role_result.scalar_one_or_none()
        
        if not user_role or (user_role.role_name.lower() not in ["superadmin", "xpiteam"]): 
            raise HTTPException(status_code=403, detail="Permission denied: Only Super Admin can update an entity")

        # Find the entity by its entity_uuid
        entity_query = select(Entity).where(Entity.entity_uuid == entity_uuid)
        entity_result = await db.execute(entity_query)
        entity = entity_result.scalar_one_or_none()
        
        if not entity:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Update fields if provided in the request
        if update_data.entity_type is not None:
            if update_data.entity_type not in ["parent", "entity"]:
                raise HTTPException(status_code=400, detail="Invalid entity_type: must be 'parent' or 'organization'")
            entity.entity_type = update_data.entity_type
        if update_data.name is not None:
            entity.name = update_data.name
        if update_data.description is not None:
            entity.description = update_data.description
        if update_data.headcount is not None:
            entity.headcount = update_data.headcount
        if update_data.domain is not None:
            entity.domain = update_data.domain
        if update_data.parent_uuid is not None:
            # Optional: Validate parent_uuid exists if required
            entity.parent_uuid = update_data.parent_uuid
        if update_data.address_id is not None:
            # Optional: Validate address_id exists in Address table if required
            entity.address_id = update_data.address_id

        # Update the updated_by and updated_on fields
        entity.updated_by = current_user.user_uuid
        entity.updated_on = datetime.utcnow()

        # Update organization in permit.io
        await permit_service.update_org(entity.entity_key, entity.name, entity.description)

        # Commit the changes
        db.add(entity)  # Ensure entity is tracked
        await db.commit()
        await db.refresh(entity)  # Refresh to get the updated object

        return {
            "message": f"Entity with entity_uuid {entity_uuid} updated successfully",
            "entity_uuid": entity.entity_uuid,
            "updated_entity": {
                "entity_type": entity.entity_type,
                "name": entity.name,
                "description": entity.description,
                "headcount": entity.headcount,
                "domain": entity.domain,
                "parent_uuid": entity.parent_uuid,
                "address_id": entity.address_id,
                "updated_by": entity.updated_by,
                "updated_on": entity.updated_on.isoformat(),
            }
        }
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Integrity error: Possibly invalid foreign key reference")
    except HTTPException as e:
        await db.rollback()
        raise e
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating organization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

async def main(entity_uuid: str, request: Request, db: AsyncSession = Depends(db)):
    """
    Main function to handle group deletion
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
    
    # Get update data from request body
    update_data = await request.json()
    
    # Convert to Pydantic model
    update_request = UpdateOrganizationRequest(**update_data)
    
    # Call update_organization with all required arguments
    return await update_organization(entity_uuid, update_request, db, user)



