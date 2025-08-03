from fastapi import HTTPException, Depends, Request
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from src.datamodel.database.userauth.AuthenticationTables import Entity
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.database.dbs.getdb import postresql as db
from sqlalchemy import select
from src.core.middleware.token_validate_middleware import validate_token
import time


logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Organization"],
        "summary": "Get organization logo",
        "response_model": dict,
        "description": "This API endpoint retrieves the logo URL for an entity. If the entity is of type 'entity', it returns the parent entity's logo.",
        "response_description": "Logo URL for the entity or its parent.",
        "deprecated": False,
    }
    return ApiConfig(**config)

async def get_entity_logo(
    db: AsyncSession = Depends(db),
    entity_uuid: Optional[str] = None,
    user_uuid: Optional[str] = None,
):
    try:

        # Get the entity from the mapping
        entity_query = select(Entity).where(Entity.entity_uuid == entity_uuid)
        entity_result = await db.execute(entity_query)
        entity = entity_result.scalar_one_or_none()
        
        if not entity:
            raise HTTPException(
                status_code=404,
                detail=f"Entity with UUID '{entity_uuid}' not found"
            )
        
        logo_url = None
        
        # If entity type is "parent", use its own logo
        if entity.entity_type == "parent":
            logo_url = entity.logo_url
        # If entity type is "entity", use its parent's logo
        elif entity.entity_type == "entity" and entity.parent_uuid:
            # Get the parent entity
            parent_query = select(Entity).where(Entity.entity_uuid == entity.parent_uuid)
            parent_result = await db.execute(parent_query)
            parent_entity = parent_result.scalar_one_or_none()
            
            if parent_entity:
                logo_url = parent_entity.logo_url
        
        if not logo_url:
            return {
                "message": "No logo found for this entity or its parent",
                "entity_uuid": entity.entity_uuid,
                "entity_type": entity.entity_type,
                "logo_url": None
            }
        
        return {
            "message": "Logo retrieved successfully",
            "entity_uuid": entity.entity_uuid,
            "entity_type": entity.entity_type,
            "logo_url": logo_url
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions to maintain their status codes
        raise
    except Exception as e:
        logger.error(f"Error retrieving entity logo: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving entity logo: {str(e)}"
        )

async def main(
    request: Request,
    db: AsyncSession = Depends(db),
):
    

    # Validate token and get user info
    validate_token_start = time.time()
    validate_token(request)
    entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid
    role_id = request.state.role_id
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    return await get_entity_logo(db, entity_uuid, user_uuid)
