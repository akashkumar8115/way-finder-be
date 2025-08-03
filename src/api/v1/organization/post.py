# from fastapi import HTTPException, Depends, Request, status
# from pydantic import BaseModel, Field, conint
# from typing import List, Optional, Dict, Literal
# from sqlalchemy.orm import Session
# from sqlalchemy.ext.asyncio import AsyncSession
# from datetime import datetime
# import logging
# from uuid import uuid4
# from src.datamodel.database.userauth.AuthenticationTables import Entity, Address, User, Role, UserEntityRoleMap
# from src.core.authentication.authentication import get_current_user
# from sqlalchemy.exc import IntegrityError
# from src.datamodel.datavalidation.apiconfig import ApiConfig  
# from src.core.database.dbs.getdb import postresql as db
# from src.services.permit.permit_service import PermitService
# from sqlalchemy import select


# logger = logging.getLogger(__name__)
# permit_service = PermitService()


# class ScreenLimits(BaseModel):
#     screen: conint(ge=0) = Field(0, description="Maximum number of screens")
#     content: conint(ge=0) = Field(0, description="Maximum number of content items")
#     playlist: conint(ge=0) = Field(0, description="Maximum number of playlists")
#     group: conint(ge=0) = Field(0, description="Maximum number of groups")
#     organization: conint(ge=0) = Field(0, description="Maximum number of organizations")  


# class EntityCreate(BaseModel):
#     entity_type: str  # "parent" or "entity"
#     name: str
#     description: Optional[str] = None  # Used for organizations
#     headcount: Optional[int] = None  # Used for parents
#     domain: Optional[str] = None  # Used for parents
#     parent_uuid: Optional[str] = None  # Reference to parent entity
#     address_id: int  # Foreign key reference
#     created_by: Optional[str] = None
#     updated_by: Optional[str] = None  
#     maxLimit: ScreenLimits = Field(
#         default_factory=ScreenLimits,
#         description="Limits for screens, content, playlists, groups, and organizations"
#     )

# def api_config():
#     config = {
#         "path": "",
#         "status_code": 201,
#         "tags": ["Organization"],
#         "summary": "Create and save Entity data",
#         "response_model": dict,
#         "description": "This API endpoint creates a new entity and saves it in the database.",
#         "response_description": "Details of the created entity.",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)

# async def update_parent_limits(db: AsyncSession, parent_uuid: str, child_limits: dict):
#     """
#     Update the parent organization's current limits when a child organization is created.
    
#     Args:
#         db: Database session
#         parent_uuid: UUID of the parent organization
#         child_limits: The limits assigned to the child organization
    
#     Returns:
#         bool: True if update was successful, False otherwise
#     """
#     try:
#         # Get the parent entity
#         parent_query = select(Entity).where(Entity.entity_uuid == parent_uuid)
#         parent_result = await db.execute(parent_query)
#         parent = parent_result.scalar_one_or_none()
        
#         if not parent:
#             logger.error(f"Parent entity with UUID {parent_uuid} not found")
#             return False
        
#         # # Check if parent has enough remaining organization limit
#         # if 'maxLimit' not in parent.__dict__ or not isinstance(parent.maxLimit, dict):
#         #     logger.error(f"Parent entity {parent_uuid} has no maxLimit attribute")
#         #     return False
        
#         # Check if parent has enough remaining organization limit
#         if parent.maxLimit.get('organization', 0) <= 0:
#             logger.error(f"Parent entity {parent_uuid} has reached its organization limit")
#             return False
        
#         # Update parent's organization limit (decrement by 1)
#         parent.currentLimit['organization'] = max(0, parent.currentLimit.get('organization', 0) + 1)
        
#         # Update other resource limits based on what was allocated to the child
#         for resource in ['screen', 'content', 'playlist', 'group']:
#             if resource in child_limits and resource in parent.maxLimit:
#                 allocated = child_limits.get(resource, 0)
#                 parent.currentLimit[resource] = max(0, parent.currentLimit.get(resource, 0) + allocated)
        
#         # Update the parent entity in the database
#         parent.updated_on = datetime.utcnow()
#         await db.commit()
        
#         return True
#     except Exception as e:
#         logger.error(f"Error updating parent limits: {str(e)}")
#         await db.rollback()
#         return False

# async def create_entity(entity_data: EntityCreate, db: AsyncSession, current_user: User):
#     try:
#         # Check if the current user has the "superadmin" role
#         role_query = select(Role).where(Role.role_id == current_user.role_id)
#         role_result = await db.execute(role_query)
#         user_role = role_result.scalar_one_or_none()

#         if not user_role or user_role.role_id not in [1, 4]:
#             raise HTTPException(status_code=403, detail="Permission denied: Only Super Admin can create an entity")
        
#         # Checking for address_id
#         address_query = select(Address).where(Address.address_id == entity_data.address_id)
#         address_result = await db.execute(address_query)
#         address = address_result.scalar_one_or_none()
        
#         if not address:
#             address_id = None
#         else:
#             address_id = entity_data.address_id
            
#         # Check if entity with same name already exists
#         entity_query = select(Entity).where(Entity.name == entity_data.name)
#         entity_result = await db.execute(entity_query)
#         existing_entity = entity_result.scalar_one_or_none()
        
#         if existing_entity:
#             raise HTTPException(status_code=409, detail=f"Entity with name '{entity_data.name}' already exists")
        
#         # If entity_type is "entity" and parent_uuid is provided, check parent's limits
#         if entity_data.entity_type == "entity" and entity_data.parent_uuid and user_role.role_id == 1:
#             # Get the user's organization
#             user_org_query = select(UserEntityRoleMap).where(
#                 UserEntityRoleMap.user_uuid == current_user.user_uuid,
#                 UserEntityRoleMap.entity_uuid == entity_data.parent_uuid  # Add this filter
#             )
#             user_org_result = await db.execute(user_org_query)
#             user_org_map = user_org_result.scalar_one_or_none()
            
#             if user_org_map:
#                 # Check if parent has enough remaining limits
#                 parent_entity_query = select(Entity).where(Entity.entity_uuid == entity_data.parent_uuid)
#                 parent_entity_result = await db.execute(parent_entity_query)
#                 parent_entity = parent_entity_result.scalar_one_or_none()
                
#                 if parent_entity and 'maxLimit' in parent_entity.__dict__:
#                     # Check if parent has reached organization limit
#                     if parent_entity.maxLimit.get('organization', 0) - parent_entity.currentLimit.get('organization', 0) <= 0:
#                         raise HTTPException(
#                             status_code=400, 
#                             detail="Parent organization has reached its maximum organization limit"
#                         )
                    
#                     # Check other resource limits
#                     limits_dict = entity_data.maxLimit.dict()
#                     for resource, limit in limits_dict.items():
#                         if limit > parent_entity.maxLimit.get(resource, 0) - parent_entity.currentLimit.get(resource, 0):
#                             raise HTTPException(
#                                 status_code=400, 
#                                 detail=f"Requested {resource} limit exceeds parent's available limit"
#                             )
        
#         # create organization in permit.io
#         new_tenant = await permit_service.create_org_only(entity_data.name, entity_data.description)

#         limits_dict = entity_data.maxLimit.dict()
        
#         # Create the new entity
#         new_entity = Entity(
#             entity_uuid=str(new_tenant.id),
#             entity_key=new_tenant.key,
#             entity_type=entity_data.entity_type,
#             name=entity_data.name,
#             description=entity_data.description,
#             headcount=entity_data.headcount,
#             domain=entity_data.domain,
#             is_active=True,
#             parent_uuid=entity_data.parent_uuid,
#             address_id=address_id,
#             created_by=current_user.user_uuid, 
#             updated_by=current_user.user_uuid,
#             created_on=datetime.utcnow(),
#             updated_on=datetime.utcnow(),
#             maxLimit=limits_dict,
#         )
#         db.add(new_entity)
#         await db.commit()
#         await db.refresh(new_entity)

#         # Update parent limits if this is a child organization created by a superadmin
#         update_result = None
#         if entity_data.entity_type == "entity" and entity_data.parent_uuid and user_role.role_id == 1:
#             update_result = await update_parent_limits(db, entity_data.parent_uuid, limits_dict)
#             if not update_result:
#                 logger.warning(f"Failed to update parent limits for parent {entity_data.parent_uuid}")

#         # Fetch the role
#         admin_role_query = select(Role).where(Role.role_id == user_role.role_id)
#         admin_role_result = await db.execute(admin_role_query)
#         admin_role = admin_role_result.scalar_one_or_none()
        
#         if not admin_role:
#             raise HTTPException(status_code=400, detail="Role does not exist")

#         # Check if a mapping already exists to avoid duplicate
#         mapping_query = select(UserEntityRoleMap).where(
#             UserEntityRoleMap.user_uuid == current_user.user_uuid,
#             UserEntityRoleMap.entity_uuid == new_entity.entity_uuid,
#             UserEntityRoleMap.role_id == user_role.role_id
#         )
#         mapping_result = await db.execute(mapping_query)
#         existing_mapping = mapping_result.scalar_one_or_none()
        
#         # Only create the mapping if it doesn't already exist
#         if not existing_mapping:
#             # Create a mapping in UserEntityRoleMap
#             role_mapping = UserEntityRoleMap(
#                 user_uuid=current_user.user_uuid,  # The user creating the entity
#                 role_id=user_role.role_id,        # The user's role
#                 entity_uuid=new_entity.entity_uuid, # The newly created entity
#                 created_on=datetime.utcnow(),
#                 updated_on=datetime.utcnow()
#             )
#             db.add(role_mapping)
#             try:
#                 await db.commit()
#             except IntegrityError as e:
#                 await db.rollback()
#                 # If we still get an integrity error, it might be a race condition
#                 # Just log it and continue since the entity was created successfully
#                 logger.warning(f"Could not create role mapping: {str(e)}")

#         response = {
#             "message": "Entity created successfully and role mapped",
#             "entity_uuid": new_entity.entity_uuid,
#             "name": new_entity.name,
#         }
        
#         if update_result is not None:
#             response["parent_limits_updated"] = update_result
            
#         return response
#     except IntegrityError as e:
#         await db.rollback()
#         logger.error(f"Integrity error: {str(e)}")
#         # Check if this is a duplicate entity name error
#         if "duplicate key" in str(e) and "entity_name_key" in str(e):
#             raise HTTPException(status_code=409, detail=f"Entity with name '{entity_data.name}' already exists")
#         # Check if this is a duplicate role mapping error
#         elif "duplicate key" in str(e) and "user_enitity_role_map_pkey" in str(e):
#             # The entity was created but the role mapping failed
#             # We can return success with a warning
#             return {
#                 "message": "Entity created successfully but role mapping already exists",
#                 "entity_uuid": new_entity.entity_uuid if 'new_entity' in locals() else None,
#                 "name": entity_data.name,
#                 "warning": "Role mapping already exists"
#             }
#         else:
#             raise HTTPException(status_code=400, detail=f"Database integrity error: {str(e)}")
#     except Exception as e:
#         await db.rollback()
#         logger.error(f"Error creating entity: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


# async def main(
#     entity_data: EntityCreate, 
#     db: AsyncSession = Depends(db), 
#     current_user: User = Depends(get_current_user)  # Get the current user
# ):
#     return await create_entity(entity_data, db, current_user)




from fastapi import HTTPException, Depends, Request, status
from pydantic import BaseModel, Field, conint
from typing import List, Optional, Dict, Literal
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging
from uuid import uuid4
from src.datamodel.database.userauth.AuthenticationTables import Entity, Address, User, Role, UserEntityRoleMap
from src.core.authentication.authentication import get_current_user
from sqlalchemy.exc import IntegrityError
from src.datamodel.datavalidation.apiconfig import ApiConfig  
from src.core.database.dbs.getdb import postresql as db
from src.services.permit.permit_service import PermitService
from sqlalchemy import select


logger = logging.getLogger(__name__)
permit_service = PermitService()


class EntityCreate(BaseModel):
    entity_type: str  # "parent" or "entity"
    name: str
    description: Optional[str] = None  # Used for organizations
    headcount: Optional[int] = None  # Used for parents
    domain: Optional[str] = None  # Used for parents
    parent_uuid: Optional[str] = None  # Reference to parent entity
    address_id: int  # Foreign key reference
    created_by: Optional[str] = None
    updated_by: Optional[str] = None  

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

async def create_entity(entity_data: EntityCreate, db: AsyncSession, current_user: User):
    try:
        # Check if the current user has the "superadmin" role
        role_query = select(Role).where(Role.role_id == current_user.role_id)
        role_result = await db.execute(role_query)
        user_role = role_result.scalar_one_or_none()

        if not user_role or user_role.role_id not in [1, 4]:
            raise HTTPException(status_code=403, detail="Permission denied: Only Super Admin can create an entity")
        
        # Checking for address_id
        address_query = select(Address).where(Address.address_id == entity_data.address_id)
        address_result = await db.execute(address_query)
        address = address_result.scalar_one_or_none()
        
        if not address:
            address_id = None
        else:
            address_id = entity_data.address_id
            
        # Check if entity with same name already exists
        entity_query = select(Entity).where(Entity.name == entity_data.name)
        entity_result = await db.execute(entity_query)
        existing_entity = entity_result.scalar_one_or_none()
        
        if existing_entity:
            raise HTTPException(status_code=409, detail=f"Entity with name '{entity_data.name}' already exists")
        
        # create organization in permit.io
        new_tenant = await permit_service.create_org_only(entity_data.name, entity_data.description)
        
        # Create the new entity
        new_entity = Entity(
            entity_uuid=str(new_tenant.id),
            entity_key=new_tenant.key,
            entity_type=entity_data.entity_type,
            name=entity_data.name,
            description=entity_data.description,
            headcount=entity_data.headcount,
            domain=entity_data.domain,
            is_active=True,
            parent_uuid=entity_data.parent_uuid,
            address_id=address_id,
            created_by=current_user.user_uuid, 
            updated_by=current_user.user_uuid,
            created_on=datetime.utcnow(),
            updated_on=datetime.utcnow(),
        )
        db.add(new_entity)
        await db.commit()
        await db.refresh(new_entity)

        # Fetch the role
        admin_role_query = select(Role).where(Role.role_id == user_role.role_id)
        admin_role_result = await db.execute(admin_role_query)
        admin_role = admin_role_result.scalar_one_or_none()
        
        if not admin_role:
            raise HTTPException(status_code=400, detail="Role does not exist")

        # Check if a mapping already exists to avoid duplicate
        mapping_query = select(UserEntityRoleMap).where(
            UserEntityRoleMap.user_uuid == current_user.user_uuid,
            UserEntityRoleMap.entity_uuid == new_entity.entity_uuid,
            UserEntityRoleMap.role_id == user_role.role_id
        )
        mapping_result = await db.execute(mapping_query)
        existing_mapping = mapping_result.scalar_one_or_none()
        
        # Only create the mapping if it doesn't already exist
        if not existing_mapping:
            # Create a mapping in UserEntityRoleMap
            role_mapping = UserEntityRoleMap(
                user_uuid=current_user.user_uuid,  # The user creating the entity
                role_id=user_role.role_id,        # The user's role
                entity_uuid=new_entity.entity_uuid, # The newly created entity
                created_on=datetime.utcnow(),
                updated_on=datetime.utcnow()
            )
            db.add(role_mapping)
            try:
                await db.commit()
            except IntegrityError as e:
                await db.rollback()
                # If we still get an integrity error, it might be a race condition
                # Just log it and continue since the entity was created successfully
                logger.warning(f"Could not create role mapping: {str(e)}")

        response = {
            "message": "Entity created successfully and role mapped",
            "entity_uuid": new_entity.entity_uuid,
            "name": new_entity.name,
        }
            
        return response
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error: {str(e)}")
        # Check if this is a duplicate entity name error
        if "duplicate key" in str(e) and "entity_name_key" in str(e):
            raise HTTPException(status_code=409, detail=f"Entity with name '{entity_data.name}' already exists")
        # Check if this is a duplicate role mapping error
        elif "duplicate key" in str(e) and "user_enitity_role_map_pkey" in str(e):
            # The entity was created but the role mapping failed
            # We can return success with a warning
            return {
                "message": "Entity created successfully but role mapping already exists",
                "entity_uuid": new_entity.entity_uuid if 'new_entity' in locals() else None,
                "name": entity_data.name,
                "warning": "Role mapping already exists"
            }
        else:
            raise HTTPException(status_code=400, detail=f"Database integrity error: {str(e)}")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating entity: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def main(
    entity_data: EntityCreate, 
    db: AsyncSession = Depends(db), 
    current_user: User = Depends(get_current_user)  # Get the current user
):
    return await create_entity(entity_data, db, current_user)
