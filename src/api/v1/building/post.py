
from fastapi import HTTPException, Depends, status, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import time
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from src.datamodel.database.domain.DigitalSignage import Building
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 201,
        "tags": ["Building"],
        "summary": "Create Building",
        "response_model": dict,
        "description": "Create a new building for the way-finder system.",
        "response_description": "Created building data",
        "deprecated": False,
    }
    return ApiConfig(**config)


class BuildingCreateRequest(BaseModel):
    name: str = Field(..., description="Name of the building")
    address: Optional[str] = Field(None, description="Building address")
    description: Optional[str] = Field(None, description="Description of the building")

    class Config:
        allow_population_by_field_name = True


class BuildingResponse(BaseModel):
    building_id: str
    name: str
    address: Optional[str] = None
    floors: List[str] = []
    description: Optional[str] = None
    entity_uuid: Optional[str] = None
    # created_by: Optional[str] = None
    datetime: float
    status: str

    class Config:
        allow_population_by_field_name = True


async def main(
    request: Request,    
    building_data: BuildingCreateRequest,
    db: AsyncSession = Depends(db)
):
    
    """Main handler for content uploads"""
    # Validate token and get user info
    validate_token_start = time.time()
    validate_token(request)
    entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    try:
        # Check if building with same name exists
        existing_building = await Building.find_one({
            "name": building_data.name,
            "entity_uuid": entity_uuid,
            "status": "active"
        })
        
        if existing_building:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Building with name '{building_data.name}' already exists"
            )

        # Create new building
        new_building = Building(
            name=building_data.name,
            address=building_data.address,
            description=building_data.description,
            entity_uuid=entity_uuid,
            floors=[],  # Empty list initially
            datetime=time.time(),
            status="active"
        )

        # Save to database
        await new_building.insert()
        
        logger.info(f"Building created successfully: {new_building.building_id}")

        # Prepare response
        response = BuildingResponse(
            building_id=new_building.building_id,
            name=new_building.name,
            address=new_building.address,
            floors=new_building.floors,
            entity_uuid=entity_uuid,
            description=new_building.description,
            datetime=new_building.datetime,
            status=new_building.status
        )

        return {
            "status": "success",
            "message": "Building created successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating building: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create building: {str(e)}"
        )


#  redis implemetn


# 2 attemp
# from fastapi import HTTPException, Depends, status, Request
# from pydantic import BaseModel, Field
# from typing import Optional, List
# import time
# import logging
# import asyncio
# from sqlalchemy.ext.asyncio import AsyncSession
# from src.datamodel.database.domain.DigitalSignage import Building
# from src.datamodel.datavalidation.apiconfig import ApiConfig
# from src.core.middleware.token_validate_middleware import validate_token
# from src.core.database.dbs.getdb import postresql as db
# from src.common.redis_utils import set_cache_fast, delete_multi_cache, redis_client
# from src.api.v1.building.get import (
#     generate_fast_cache_key, add_to_memory_cache, _MEMORY_CACHE, _CACHE_ACCESS_ORDER, MAX_MEMORY_CACHE
# )

# logger = logging.getLogger(__name__)

# CACHE_KEYS = {
#     "building": "bld:{entity_uuid}:{building_id}",
#     "list": "bld_list:{entity_uuid}",
#     "active_list": "buildings:active:{entity_uuid}",
#     "inactive_list": "buildings:inactive:{entity_uuid}",
# }
# CACHE_TTL = {
#     "building": 3600,
#     "list": 900,
# }

# def api_config():
#     config = {
#         "path": "",
#         "status_code": 201,
#         "tags": ["Building"],
#         "summary": "Create Building",
#         "response_model": dict,
#         "description": "Create a new building for the way-finder system.",
#         "response_description": "Created building data",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)

# class BuildingCreateRequest(BaseModel):
#     name: str = Field(..., description="Name of the building")
#     address: Optional[str] = Field(None, description="Building address")
#     description: Optional[str] = Field(None, description="Description of the building")
#     class Config:
#         allow_population_by_field_name = True

# class BuildingResponse(BaseModel):
#     building_id: str
#     name: str
#     address: Optional[str] = None
#     floors: List[str] = []
#     description: Optional[str] = None
#     entity_uuid: Optional[str] = None
#     datetime: float
#     status: str
#     class Config:
#         allow_population_by_field_name = True

# def invalidate_memory_cache_by_entity(entity_uuid: str):
#     keys_to_delete = [key for key in _MEMORY_CACHE if key.startswith(f"b:{entity_uuid[-12:]}")]
#     for key in keys_to_delete:
#         _MEMORY_CACHE.pop(key, None)
#         try: _CACHE_ACCESS_ORDER.remove(key)
#         except ValueError: pass
#     return keys_to_delete

# async def invalidate_redis_caches(entity_uuid: str):
#     # Wildcard deletion for related list caches
#     patterns = [
#         CACHE_KEYS["list"].format(entity_uuid=entity_uuid) + "*",
#         CACHE_KEYS["active_list"].format(entity_uuid=entity_uuid) + "*",
#         CACHE_KEYS["inactive_list"].format(entity_uuid=entity_uuid) + "*",
#     ]
#     for pattern in patterns:
#         try:
#             keys = await redis_client.keys(pattern)
#             if keys:
#                 await redis_client.delete(*keys)
#         except Exception as e:
#             logger.warning(f"Pattern deletion error for {pattern}: {e}")

# async def main(
#     request: Request,
#     building_data: BuildingCreateRequest,
#     db: AsyncSession = Depends(db)
# ):
#     validate_token_start = time.time()
#     validate_token(request)
#     entity_uuid = request.state.entity_uuid
#     user_uuid = request.state.user_uuid
#     validate_token_time = time.time() - validate_token_start
#     logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")
#     try:
#         # Duplicate name check (active only)
#         existing_building = await Building.find_one({
#             "name": building_data.name,
#             "entity_uuid": entity_uuid,
#             "status": "active"
#         })
#         if existing_building:
#             raise HTTPException(
#                 status_code=status.HTTP_409_CONFLICT,
#                 detail=f"Building with name '{building_data.name}' already exists"
#             )

#         # Create building
#         new_building = Building(
#             name=building_data.name,
#             address=building_data.address,
#             description=building_data.description,
#             entity_uuid=entity_uuid,
#             floors=[],
#             datetime=time.time(),
#             status="active"
#         )
#         await new_building.insert()
#         logger.info(f"Building created: {new_building.building_id}")

#         response = BuildingResponse(
#             building_id=new_building.building_id,
#             name=new_building.name,
#             address=new_building.address,
#             floors=new_building.floors,
#             entity_uuid=entity_uuid,
#             description=new_building.description,
#             datetime=new_building.datetime,
#             status="active"
#         )

#         # ---- Cache Handling ----
#         try:
#             # Invalidate memory cache for building lists for this entity
#             mem_keys = invalidate_memory_cache_by_entity(entity_uuid)
#             # Invalidate Redis caches for lists (wildcard patterns)
#             asyncio.create_task(invalidate_redis_caches(entity_uuid))
#             # Optionally cache the single building response (by building_id)
#             single_key = CACHE_KEYS["building"].format(entity_uuid=entity_uuid, building_id=new_building.building_id)
#             cache_data = {"status": "success", "data": response.dict()}
#             asyncio.create_task(set_cache_fast(single_key, cache_data, expire=CACHE_TTL["building"]))
#             add_to_memory_cache(single_key, cache_data)
#             logger.info(f"Invalidated {len(mem_keys)} memory caches, updated single building cache.")

#         except Exception as cache_err:
#             logger.warning(f"Cache update failed after building create: {cache_err}")

#         return {
#             "status": "success",
#             "message": "Building created successfully",
#             "data": response.dict()
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception(f"Error creating building: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to create building: {str(e)}"
#         )
