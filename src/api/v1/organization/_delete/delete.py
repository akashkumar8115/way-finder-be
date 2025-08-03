# from fastapi import HTTPException, Depends, Request, status
# import logging
# from bson import ObjectId
# import asyncio
# from typing import Dict, List
# from src.datamodel.datavalidation.apiconfig import ApiConfig
# from src.core.authentication.authentication import get_current_user, get_token_payload
# from src.datamodel.database.userauth.AuthenticationTables import Entity, Role, User, UserEntityRoleMap
# from sqlalchemy.exc import IntegrityError
# from src.core.database.dbs.getdb import postresql as db
# from sqlalchemy.orm import Session
# from sqlalchemy.ext.asyncio import AsyncSession
# from src.services.permit.permit_service import PermitService
# from sqlalchemy import select
# import time
# from src.core.middleware.token_validate_middleware import validate_token
# from datetime import datetime

# logger = logging.getLogger(__name__)
# permit_service = PermitService()

# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Organization"],
#         "summary": "Delete organization",
#         "response_model": None,
#         "description": "This API endpoint deletes an organization and its associated users and role mappings.",
#         "response_description": "Details of the deletion operation.",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)

# async def update_parent_limits_on_deletion(db: AsyncSession, parent_uuid: str, child_limits: dict):
#     """
#     Update the parent organization's current limits when a child organization is deleted.
#     Increases the available limits by the amount that was allocated to the child.
    
#     Args:
#         db: Database session
#         parent_uuid: UUID of the parent organization
#         child_limits: The limits that were assigned to the child organization
    
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
        
#         # Increase parent's organization limit (since a child org is being deleted)
#         parent.currentLimit['organization'] = max(0, parent.currentLimit.get('organization', 0) - 1)
        
#         # Update other resource limits based on what was allocated to the child
#         for resource in ['screen', 'content', 'playlist', 'group']:
#             if resource in child_limits and resource in parent.currentLimit:
#                 freed_up = child_limits.get(resource, 0)
#                 parent.currentLimit[resource] = max(0, parent.currentLimit.get(resource, 0) - freed_up)
        
#         # Update the parent entity in the database
#         parent.updated_on = datetime.utcnow()
#         await db.commit()
        
#         return True
#     except Exception as e:
#         logger.error(f"Error updating parent limits on deletion: {str(e)}")
#         await db.rollback()
#         return False

# async def delete_organization(entity_uuid: str, user_uuid: str, db: AsyncSession):
#     try:
#         # Check Super Admin access
#         query = select(UserEntityRoleMap).where(
#             UserEntityRoleMap.user_uuid == user_uuid,
#             UserEntityRoleMap.role_id.in_([4, 1])  # Check if role_id is 4 or 1
#         )
#         result = await db.execute(query)
#         is_superadmin = result.scalars().first()  # Use scalars().first()
        
#         if not is_superadmin:
#             raise HTTPException(status_code=403, detail="User is not a Super Admin of this entity")

#         # Get the entity to delete
#         entity_query = select(Entity).where(Entity.entity_uuid == entity_uuid)
#         entity_result = await db.execute(entity_query)
#         tenant = entity_result.scalar_one_or_none()  # This is fine as we expect only one entity
        
#         if not tenant:
#             raise HTTPException(status_code=404, detail="Entity not found")
#         tenant_key = tenant.entity_key

#         # Store entity information before deletion
#         entity_type = tenant.entity_type
#         parent_uuid = tenant.parent_uuid
#         max_limits = tenant.maxLimit if hasattr(tenant, 'maxLimit') else {}
        
#         # Get all users linked to this entity
#         user_roles_query = select(UserEntityRoleMap).where(UserEntityRoleMap.entity_uuid == entity_uuid)
#         user_roles_result = await db.execute(user_roles_query)
#         user_roles = user_roles_result.scalars().all()
        
#         user_uuids = [ur.user_uuid for ur in user_roles]

#         # Delete the org from permit.io
#         try:
#             await permit_service.delete_org(tenant_key)
#         except Exception as e:
#             logger.error(f"Error deleting organization from Permit.io: {str(e)}")
#             # Continue with deletion even if Permit.io deletion fails

#         # Delete all User-Role mappings for this entity - FIRST TRANSACTION
#         for user_role in user_roles:
#             await db.delete(user_role)
        
#         # Commit the deletion of mappings before proceeding
#         await db.commit()

#         # Delete users only if they're not linked to any other entity - SECOND TRANSACTION
#         for user_uuid in set(user_uuids):
#             # Check if user is linked elsewhere
#             linked_query = select(UserEntityRoleMap).where(
#                 UserEntityRoleMap.user_uuid == user_uuid,
#                 UserEntityRoleMap.entity_uuid != entity_uuid
#             )
#             linked_result = await db.execute(linked_query)
#             is_linked_elsewhere = linked_result.scalars().first()  # Use scalars().first() here too
            
#             if not is_linked_elsewhere:
#                 # Delete the user if not linked elsewhere
#                 user_query = select(User).where(User.user_uuid == user_uuid)
#                 user_result = await db.execute(user_query)
#                 user = user_result.scalar_one_or_none()  # This is fine as we expect only one user
                
#                 if user:
#                     await db.delete(user)
        
#         # Commit user deletions
#         await db.commit()

#         # Delete the entity itself - THIRD TRANSACTION
#         await db.delete(tenant)
#         await db.commit()
        
#         # Update parent limits if this was a child entity
#         update_result = None
#         if entity_type == "entity" and parent_uuid:
#             update_result = await update_parent_limits_on_deletion(db, parent_uuid, max_limits)
#             if not update_result:
#                 logger.warning(f"Failed to update parent limits for parent {parent_uuid}")
        
#         response = {
#             "message": "Entity and associated users and role mappings deleted successfully"
#         }
        
#         if update_result is not None:
#             response["parent_limits_updated"] = update_result
            
#         return response

#     except HTTPException as e:
#         await db.rollback()
#         raise e
#     except Exception as e:
#         await db.rollback()
#         logger.error(f"Error while deleting organization: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# async def main(entity_uuid: str, request: Request, db: AsyncSession = Depends(db)):
#     # Get entity_uuid from request
#     validate_token_start = time.time()
    
#     validate_token(request)
#     # await verify_permissions(request, "content", "read")

#     # entity_uuid = request.state.entity_uuid
#     user_uuid = request.state.user_uuid
#     validate_token_time = time.time() - validate_token_start
#     logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")
    
#     return await delete_organization(entity_uuid, user_uuid, db)


from fastapi import HTTPException, Depends, Request, status
import logging
from bson import ObjectId
import asyncio
from typing import Dict, List
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.authentication.authentication import get_current_user, get_token_payload
from src.datamodel.database.userauth.AuthenticationTables import Entity, Role, User, UserEntityRoleMap
from sqlalchemy.exc import IntegrityError
from src.core.database.dbs.getdb import postresql as db
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.permit.permit_service import PermitService
from sqlalchemy import select
import time
from src.core.middleware.token_validate_middleware import validate_token
from datetime import datetime

logger = logging.getLogger(__name__)
permit_service = PermitService()

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Organization"],
        "summary": "Delete organization",
        "response_model": None,
        "description": "This API endpoint deletes an organization and its associated users and role mappings.",
        "response_description": "Details of the deletion operation.",
        "deprecated": False,
    }
    return ApiConfig(**config)

async def delete_organization(entity_uuid: str, user_uuid: str, db: AsyncSession):
    try:
        # Check Super Admin access
        query = select(UserEntityRoleMap).where(
            UserEntityRoleMap.user_uuid == user_uuid,
            UserEntityRoleMap.role_id.in_([4, 1])  # Check if role_id is 4 or 1
        )
        result = await db.execute(query)
        is_superadmin = result.scalars().first()  # Use scalars().first()
        
        if not is_superadmin:
            raise HTTPException(status_code=403, detail="User is not a Super Admin of this entity")

        # Get the entity to delete
        entity_query = select(Entity).where(Entity.entity_uuid == entity_uuid)
        entity_result = await db.execute(entity_query)
        tenant = entity_result.scalar_one_or_none()  # This is fine as we expect only one entity
        
        if not tenant:
            raise HTTPException(status_code=404, detail="Entity not found")
        tenant_key = tenant.entity_key

        # Store entity information before deletion
        entity_type = tenant.entity_type
        parent_uuid = tenant.parent_uuid
        
        # Get all users linked to this entity
        user_roles_query = select(UserEntityRoleMap).where(UserEntityRoleMap.entity_uuid == entity_uuid)
        user_roles_result = await db.execute(user_roles_query)
        user_roles = user_roles_result.scalars().all()
        
        user_uuids = [ur.user_uuid for ur in user_roles]

        # Delete the org from permit.io
        try:
            await permit_service.delete_org(tenant_key)
        except Exception as e:
            logger.error(f"Error deleting organization from Permit.io: {str(e)}")
            # Continue with deletion even if Permit.io deletion fails

        # Delete all User-Role mappings for this entity - FIRST TRANSACTION
        for user_role in user_roles:
            await db.delete(user_role)
        
        # Commit the deletion of mappings before proceeding
        await db.commit()

        # Delete users only if they're not linked to any other entity - SECOND TRANSACTION
        for user_uuid in set(user_uuids):
            # Check if user is linked elsewhere
            linked_query = select(UserEntityRoleMap).where(
                UserEntityRoleMap.user_uuid == user_uuid,
                UserEntityRoleMap.entity_uuid != entity_uuid
            )
            linked_result = await db.execute(linked_query)
            is_linked_elsewhere = linked_result.scalars().first()  # Use scalars().first() here too
            
            if not is_linked_elsewhere:
                # Delete the user if not linked elsewhere
                user_query = select(User).where(User.user_uuid == user_uuid)
                user_result = await db.execute(user_query)
                user = user_result.scalar_one_or_none()  # This is fine as we expect only one user
                
                if user:
                    await db.delete(user)
        
        # Commit user deletions
        await db.commit()

        # Delete the entity itself - THIRD TRANSACTION
        await db.delete(tenant)
        await db.commit()
        
        response = {
            "message": "Entity and associated users and role mappings deleted successfully"
        }
            
        return response

    except HTTPException as e:
        await db.rollback()
        raise e
    except Exception as e:
        await db.rollback()
        logger.error(f"Error while deleting organization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

async def main(entity_uuid: str, request: Request, db: AsyncSession = Depends(db)):
    # Get entity_uuid from request
    validate_token_start = time.time()
    
    validate_token(request)
    # await verify_permissions(request, "content", "read")

    # entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")
    
    return await delete_organization(entity_uuid, user_uuid, db)
