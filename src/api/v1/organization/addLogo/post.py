from fastapi import HTTPException, Depends, UploadFile, File, status, Request
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime
import logging
import re
from src.datamodel.database.userauth.AuthenticationTables import Entity, Role, User
from src.core.authentication.authentication import get_current_user
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
        "summary": "Upload and set organization logo",
        "response_model": dict,
        "description": "This API endpoint uploads or updates a logo for an organization and updates the entity record.",
        "response_description": "Details of the updated entity with logo URL.",
        "deprecated": False,
    }
    return ApiConfig(**config)

async def upload_entity_logo(
    entity_uuid: str,
    logo: UploadFile = File(...),
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
                detail="Permission denied: Only Super Admin or Xpi Team can update entity logo"
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
        
        # Validate file type
        if logo.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only JPEG, PNG, GIF, and WEBP images are allowed."
            )
        
        # Check if entity already has a logo
        previous_logo_url = entity.logo_url
        previous_object_name = None
        
        # Extract the object path from the previous logo URL if it exists
        if previous_logo_url:
            # URL format is like: https://minio-endpoint/bucket-name/folder/file.ext
            # We need to extract the path after the bucket name
            try:
                # Use regex to extract the object path
                match = re.search(f'/{MINIO_BUCKET}/(.+)$', previous_logo_url)
                if match:
                    previous_object_name = match.group(1)
                    logger.info(f"Previous logo object path: {previous_object_name}")
            except Exception as e:
                logger.warning(f"Could not parse previous logo URL: {str(e)}")
        
        # Upload new logo to MinIO
        folder = f"organizations/{entity_uuid}"
        upload_result = await minio_service.upload_file(logo, folder)
        
        if not upload_result or "content_url" not in upload_result:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload logo file"
            )
        
        # Update entity with new logo URL
        entity.logo_url = upload_result["content_url"]
        entity.updated_by = user_uuid
        entity.updated_on = datetime.utcnow()
        
        await db.commit()
        await db.refresh(entity)
        
        # Delete previous logo from MinIO if it exists
        if previous_object_name:
            try:
                delete_result = await minio_service.delete_file(previous_object_name)
                logger.info(f"Deleted previous logo: {delete_result}")
            except Exception as e:
                logger.warning(f"Failed to delete previous logo: {str(e)}")
                # Continue even if delete fails
        
        action_type = "updated" if previous_logo_url else "added"
        
        return {
            "message": f"Logo {action_type} and entity updated successfully",
            "entity_uuid": entity.entity_uuid,
            "name": entity.name,
            "logo_url": entity.logo_url
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions to maintain their status codes
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating entity logo: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while updating entity logo: {str(e)}"
        )

async def main(
    entity_uuid: str,
    request: Request,
    logo: UploadFile = File(...),
    db: AsyncSession = Depends(db),
):
    # Validate token and get user info
    validate_token_start = time.time()
    validate_token(request)
    # entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid
    role_id = request.state.role_id
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    return await upload_entity_logo(entity_uuid, logo, db, role_id, user_uuid)

