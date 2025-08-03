from fastapi import HTTPException, Depends, status, Request
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import re
from datetime import datetime
import logging
from src.datamodel.database.userauth.AuthenticationTables import Entity, Role
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.database.dbs.getdb import postresql as db
from src.services.files.minio_service import MinioService, MINIO_BUCKET
from sqlalchemy import select
from src.core.middleware.token_validate_middleware import validate_token
import time

logger = logging.getLogger(__name__)
minio_service = MinioService()

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Organization"],
        "summary": "Remove organization logo",
        "response_model": dict,
        "description": "This API endpoint removes the logo from an organization and updates the entity record.",
        "response_description": "Details of the updated entity with logo removed.",
        "deprecated": False,
    }
    return ApiConfig(**config)

async def remove_entity_logo(
    entity_uuid: str,
    db: AsyncSession = Depends(db),
    role_id: Optional[int] = None,
    user_uuid: Optional[str] = None,
):
    try:
        # Check if the current user has the required role (1 or 4)
        role_query = select(Role).where(Role.role_id == role_id)
        role_result = await db.execute(role_query)
        user_role = role_result.scalar_one_or_none()

        if not user_role or user_role.role_id not in [1, 4]:
            raise HTTPException(
                status_code=403, 
                detail="Permission denied: Only Super Admin or Admin can remove entity logo"
            )
        
        # Check if entity exists
        entity_query = select(Entity).where(Entity.entity_uuid == entity_uuid)
        entity_result = await db.execute(entity_query)
        entity = entity_result.scalar_one_or_none()
        
        if not entity:
            raise HTTPException(
                status_code=404,
                detail=f"Entity with UUID '{entity_uuid}' not found"
            )
        
        # Check if entity has a logo
        if not entity.logo_url:
            raise HTTPException(
                status_code=404,
                detail="Entity does not have a logo to remove"
            )
        
        # Extract the object path from the logo URL
        previous_logo_url = entity.logo_url
        previous_object_name = None
        
        try:
            # Use regex to extract the object path
            match = re.search(f'/{MINIO_BUCKET}/(.+)$', previous_logo_url)
            if match:
                previous_object_name = match.group(1)
                logger.info(f"Logo object path to remove: {previous_object_name}")
        except Exception as e:
            logger.warning(f"Could not parse logo URL: {str(e)}")
        
        # Update entity to remove logo URL
        entity.logo_url = None
        entity.updated_by = user_uuid
        entity.updated_on = datetime.utcnow()
        
        await db.commit()
        await db.refresh(entity)
        
        # Delete logo from MinIO if object path was extracted
        if previous_object_name:
            try:
                delete_result = await minio_service.delete_file(previous_object_name)
                logger.info(f"Deleted logo: {delete_result}")
            except Exception as e:
                logger.warning(f"Failed to delete logo from storage: {str(e)}")
                # Continue even if delete fails
        
        return {
            "message": "Logo removed successfully",
            "entity_uuid": entity.entity_uuid,
            "name": entity.name
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions to maintain their status codes
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error removing entity logo: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while removing entity logo: {str(e)}"
        )

async def main(
    entity_uuid: str,
    request: Request,
    db: AsyncSession = Depends(db),
):
    # Validate token and get user info
    validate_token_start = time.time()
    validate_token(request)
    user_uuid = request.state.user_uuid
    role_id = request.state.role_id
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    return await remove_entity_logo(entity_uuid, db, role_id, user_uuid)
