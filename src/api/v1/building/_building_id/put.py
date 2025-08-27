# from fastapi import HTTPException, Depends, status, Request
# from pydantic import BaseModel, Field
# from typing import Optional
# import time
# import logging
# from sqlalchemy.ext.asyncio import AsyncSession
# from src.datamodel.database.domain.DigitalSignage import Building
# from src.datamodel.datavalidation.apiconfig import ApiConfig
# from src.core.middleware.token_validate_middleware import validate_token
# from src.core.database.dbs.getdb import postresql as db


# logger = logging.getLogger(__name__)


# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Building"],
#         "summary": "Update Building",
#         "response_model": dict,
#         "description": "Update an existing building in the way-finder system.",
#         "response_description": "Updated building data",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)


# class BuildingUpdateRequest(BaseModel):
#     name: Optional[str] = Field(None, description="Name of the building")
#     address: Optional[str] = Field(None, description="Building address")
#     description: Optional[str] = Field(None, description="Description of the building")
#     status: Optional[str] = Field(None, description="Building status (active/inactive)")

#     class Config:
#         allow_population_by_field_name = True


# class BuildingResponse(BaseModel):
#     building_id: str
#     name: str
#     address: Optional[str] = None
#     floors: list = []
#     description: Optional[str] = None
#     entity_uuid: Optional[str] = None
#     datetime: float
#     update_on: Optional[float] = None
#     updated_by: Optional[str] = None
#     status: str

#     class Config:
#         allow_population_by_field_name = True


# async def main(
#     request: Request,
#     building_id: str,
#     building_data: BuildingUpdateRequest,
#     db: AsyncSession = Depends(db)
# ):
#     """Main handler for building updates"""
#     # Validate token and get user info
#     validate_token_start = time.time()
#     validate_token(request)
#     entity_uuid = request.state.entity_uuid
#     user_uuid = request.state.user_uuid
#     validate_token_time = time.time() - validate_token_start
#     logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

#     try:
#         # Find the existing building
#         existing_building = await Building.find_one({
#             "building_id": building_id,
#             "entity_uuid": entity_uuid,
#             "status": {"$ne": "deleted"}  # Exclude deleted buildings
#         })
        
#         if not existing_building:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Building with ID '{building_id}' not found"
#             )

#         # Check if name is being updated and if it conflicts with existing buildings
#         if building_data.name and building_data.name != existing_building.name:
#             name_conflict = await Building.find_one({
#                 "name": building_data.name,
#                 "entity_uuid": entity_uuid,
#                 "building_id": {"$ne": building_id},  # Exclude current building
#                 "status": "active"
#             })
            
#             if name_conflict:
#                 raise HTTPException(
#                     status_code=status.HTTP_409_CONFLICT,
#                     detail=f"Building with name '{building_data.name}' already exists"
#                 )

#         # Update only provided fields
#         update_data = {}
#         if building_data.name is not None:
#             update_data["name"] = building_data.name
#         if building_data.address is not None:
#             update_data["address"] = building_data.address
#         if building_data.description is not None:
#             update_data["description"] = building_data.description
#         if building_data.status is not None:
#             # Validate status values
#             if building_data.status not in ["active", "inactive"]:
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail="Status must be either 'active' or 'inactive'"
#                 )
#             update_data["status"] = building_data.status

#         # Add update metadata
#         update_data["update_on"] = time.time()
#         update_data["updated_by"] = user_uuid

#         # Update the building
#         await existing_building.update({"$set": update_data})
        
#         # Refresh the building data
#         updated_building = await Building.find_one({"building_id": building_id})
        
#         logger.info(f"Building updated successfully: {building_id}")

#         # Prepare response
#         response = BuildingResponse(
#             building_id=updated_building.building_id,
#             name=updated_building.name,
#             address=updated_building.address,
#             floors=updated_building.floors or [],
#             entity_uuid=updated_building.entity_uuid,
#             description=updated_building.description,
#             datetime=updated_building.datetime,
#             update_on=updated_building.update_on,
#             updated_by=updated_building.updated_by,
#             status=updated_building.status
#         )

#         return {
#             "status": "success",
#             "message": "Building updated successfully",
#             "data": response
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception(f"Error updating building: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to update building: {str(e)}"
#         )


# from fastapi import HTTPException, Depends, status, Request
# from pydantic import BaseModel, Field
# from typing import Optional
# import time
# import logging
# import asyncio
# from sqlalchemy.ext.asyncio import AsyncSession
# from src.datamodel.database.domain.DigitalSignage import Building
# from src.datamodel.datavalidation.apiconfig import ApiConfig
# from src.core.middleware.token_validate_middleware import validate_token
# from src.core.database.dbs.getdb import postresql as db

# # Import your existing Redis utilities
# from src.common.redis_utils import (
#     get_cache_fast, 
#     set_cache_fast, 
#     get_multi_cache_fast, 
#     set_multi_cache_fast,
#     set_cache_background,
#     redis_client
# )

# logger = logging.getLogger(__name__)

# # Cache configuration
# CACHE_TTL = {
#     "building": 9000,    # 150 minutes for building data (relatively stable)
#     "result": 3000,      # 50 minutes for final response
#     "list": 1800,        # 30 minutes for building lists
# }

# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Building"],
#         "summary": "Update Building",
#         "response_model": dict,
#         "description": "Update an existing building in the way-finder system.",
#         "response_description": "Updated building data",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)


# class BuildingUpdateRequest(BaseModel):
#     name: Optional[str] = Field(None, description="Name of the building")
#     address: Optional[str] = Field(None, description="Building address")
#     description: Optional[str] = Field(None, description="Description of the building")
#     status: Optional[str] = Field(None, description="Building status (active/inactive)")

#     class Config:
#         allow_population_by_field_name = True


# class BuildingResponse(BaseModel):
#     building_id: str
#     name: str
#     address: Optional[str] = None
#     floors: list = []
#     description: Optional[str] = None
#     entity_uuid: Optional[str] = None
#     datetime: float
#     update_on: Optional[float] = None
#     updated_by: Optional[str] = None
#     status: str

#     class Config:
#         allow_population_by_field_name = True


# async def _get_building_cached(building_id: str, entity_uuid: str) -> Optional[Building]:
#     """Get building data with caching"""
#     cache_key = f"building:{entity_uuid}:{building_id}"
    
#     # Try cache first
#     cached_building = await get_cache_fast(cache_key)
#     if cached_building is not None:
#         logger.info(f"Cache hit for building update: {building_id}")
#         try:
#             return Building(**cached_building)
#         except Exception as e:
#             logger.warning(f"Error converting cached building data: {e}")
#             # Continue to database fetch if conversion fails
    
#     # Cache miss - fetch from database
#     logger.info(f"Cache miss for building update: {building_id}")
#     try:
#         building = await Building.find_one({
#             "building_id": building_id,
#             "entity_uuid": entity_uuid,
#             "status": {"$ne": "deleted"}
#         })
        
#         if building:
#             # Cache the building data in background
#             try:
#                 building_dict = building.dict()
#                 await set_cache_background(cache_key, building_dict, expire=CACHE_TTL["building"])
#             except Exception as e:
#                 logger.warning(f"Error caching building data: {e}")
        
#         return building
        
#     except Exception as e:
#         logger.error(f"Error fetching building from database: {e}")
#         return None

# async def _check_name_conflict_cached(name: str, entity_uuid: str, building_id: str) -> bool:
#     """Check for name conflicts with caching"""
#     cache_key = f"building_names:{entity_uuid}:{name}"
    
#     # Try cache first
#     cached_conflict = await get_cache_fast(cache_key)
#     if cached_conflict is not None:
#         # If cached result shows a conflict, verify it's not the current building
#         if cached_conflict.get('building_id') != building_id:
#             logger.info(f"Cache hit for name conflict check: {name}")
#             return True
#         return False
    
#     # Cache miss - check database
#     name_conflict = await Building.find_one({
#         "name": name,
#         "entity_uuid": entity_uuid,
#         "building_id": {"$ne": building_id},
#         "status": "active"
#     })
    
#     # Cache the result
#     if name_conflict:
#         conflict_data = {"building_id": name_conflict.building_id, "exists": True}
#         await set_cache_background(cache_key, conflict_data, expire=CACHE_TTL["list"])
#         return True
#     else:
#         no_conflict_data = {"building_id": None, "exists": False}
#         await set_cache_background(cache_key, no_conflict_data, expire=300)  # Cache "no conflict" for shorter time
#         return False

# async def _invalidate_related_cache(building_id: str, entity_uuid: str, old_name: str = None, new_name: str = None):
#     """Invalidate all related cache entries"""
#     cache_keys_to_clear = [
#         f"building:{entity_uuid}:{building_id}",
#         f"building_detail:{building_id}",
#         f"buildings:list:{entity_uuid}",
#         f"buildings:active:{entity_uuid}",
#         f"entity:{entity_uuid}:buildings",
#     ]
    
#     # Clear name-specific caches
#     if old_name:
#         cache_keys_to_clear.append(f"building_names:{entity_uuid}:{old_name}")
#     if new_name:
#         cache_keys_to_clear.append(f"building_names:{entity_uuid}:{new_name}")
    
#     # Clear all related caches in background
#     for cache_key in cache_keys_to_clear:
#         asyncio.create_task(redis_client.delete(cache_key))
    
#     logger.info(f"Invalidated {len(cache_keys_to_clear)} cache keys for building {building_id}")

# async def main(
#     request: Request,
#     building_id: str,
#     building_data: BuildingUpdateRequest,
#     db: AsyncSession = Depends(db)
# ):
#     """Main handler for building updates"""
#     # Validate token and get user info
#     validate_token_start = time.time()
#     validate_token(request)
#     entity_uuid = request.state.entity_uuid
#     user_uuid = request.state.user_uuid
#     validate_token_time = time.time() - validate_token_start
#     logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

#     try:
#         # Get existing building from cache or database
#         db_fetch_start = time.time()
#         existing_building = await _get_building_cached(building_id, entity_uuid)
#         db_fetch_time = time.time() - db_fetch_start
#         logger.info(f"PERFORMANCE: Building fetch took {db_fetch_time:.4f} seconds")
        
#         if not existing_building:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Building with ID '{building_id}' not found"
#             )

#         old_name = existing_building.name

#         # Check if name is being updated and if it conflicts
#         if building_data.name and building_data.name != existing_building.name:
#             name_check_start = time.time()
#             has_conflict = await _check_name_conflict_cached(building_data.name, entity_uuid, building_id)
#             name_check_time = time.time() - name_check_start
#             logger.info(f"PERFORMANCE: Name conflict check took {name_check_time:.4f} seconds")
            
#             if has_conflict:
#                 raise HTTPException(
#                     status_code=status.HTTP_409_CONFLICT,
#                     detail=f"Building with name '{building_data.name}' already exists"
#                 )

#         # Update only provided fields
#         update_data = {}
#         if building_data.name is not None:
#             update_data["name"] = building_data.name
#         if building_data.address is not None:
#             update_data["address"] = building_data.address
#         if building_data.description is not None:
#             update_data["description"] = building_data.description
#         if building_data.status is not None:
#             # Validate status values
#             if building_data.status not in ["active", "inactive"]:
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail="Status must be either 'active' or 'inactive'"
#                 )
#             update_data["status"] = building_data.status

#         # Add update metadata
#         update_data["update_on"] = time.time()
#         update_data["updated_by"] = user_uuid

#         # Update the building in database
#         update_start = time.time()
#         await existing_building.update({"$set": update_data})
#         update_time = time.time() - update_start
#         logger.info(f"PERFORMANCE: Database update took {update_time:.4f} seconds")
        
#         # Refresh the building data
#         updated_building = await Building.find_one({"building_id": building_id})
        
#         # Invalidate related caches after successful update
#         await _invalidate_related_cache(
#             building_id, 
#             entity_uuid, 
#             old_name=old_name if building_data.name else None,
#             new_name=building_data.name
#         )
        
#         logger.info(f"Building updated successfully: {building_id}")

#         # Prepare response
#         response = BuildingResponse(
#             building_id=updated_building.building_id,
#             name=updated_building.name,
#             address=updated_building.address,
#             floors=updated_building.floors or [],
#             entity_uuid=updated_building.entity_uuid,
#             description=updated_building.description,
#             datetime=updated_building.datetime,
#             update_on=updated_building.update_on,
#             updated_by=updated_building.updated_by,
#             status=updated_building.status
#         )

#         result = {
#             "status": "success",
#             "message": "Building updated successfully",
#             "data": response.dict()
#         }

#         # Cache the updated building data in background
#         building_cache_key = f"building:{entity_uuid}:{building_id}"
#         await set_cache_background(building_cache_key, updated_building.dict(), expire=CACHE_TTL["building"])
        
#         # Cache the response for quick retrieval
#         result_cache_key = f"building_update_result:{building_id}:{int(time.time())}"
#         await set_cache_background(result_cache_key, result, expire=CACHE_TTL["result"])

#         # Log performance metrics
#         total_time = time.time() - validate_token_start
#         logger.info(f"PERFORMANCE: Total update operation took {total_time:.4f} seconds")

#         return result

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception(f"Error updating building: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to update building: {str(e)}"
#         )

# 3rd improve
from fastapi import HTTPException, Depends, status, Request, Path
from pydantic import BaseModel, Field, validator
from typing import Optional
import time
import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from src.datamodel.database.domain.DigitalSignage import Building
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db

# Import your existing Redis utilities
from src.common.redis_utils import (
    get_cache_fast, 
    set_cache_fast, 
    get_multi_cache_fast, 
    set_multi_cache_fast,
    set_cache_background,
    redis_client
)

logger = logging.getLogger(__name__)

# Optimized Cache configuration
CACHE_TTL = {
    "building": 7200,       # 2 hours for building data
    "result": 1800,         # 30 minutes for API responses
    "list": 900,            # 15 minutes for building lists
    "name_check": 600,      # 10 minutes for name conflict checks
    "negative": 300,        # 5 minutes for negative results
}

# Cache key patterns
CACHE_KEYS = {
    "building": "bld:{entity_uuid}:{building_id}",
    "name_check": "bld_name:{entity_uuid}:{name}",
    "list": "bld_list:{entity_uuid}",
    "result": "bld_upd:{building_id}:{timestamp}",
    "entity_buildings": "entity:{entity_uuid}:buildings"
}

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Building"],
        "summary": "Update Building",
        "response_model": dict,
        "description": "Update an existing building in the way-finder system with optimized caching.",
        "response_description": "Updated building data",
        "deprecated": False,
    }
    return ApiConfig(**config)

class BuildingUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Name of the building")
    address: Optional[str] = Field(None, max_length=500, description="Building address")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the building")
    status: Optional[str] = Field(None, description="Building status (active/inactive)")

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('Name cannot be empty or whitespace')
        return v

    @validator('status')
    def validate_status(cls, v):
        if v is not None and v not in ["active", "inactive"]:
            raise ValueError('Status must be either "active" or "inactive"')
        return v

    class Config:
        allow_population_by_field_name = True

class BuildingResponse(BaseModel):
    building_id: str
    name: str
    address: Optional[str] = None
    floors: list = []
    description: Optional[str] = None
    entity_uuid: Optional[str] = None
    datetime: float
    update_on: Optional[float] = None
    updated_by: Optional[str] = None
    status: str

    class Config:
        allow_population_by_field_name = True
        from_attributes = True

async def _get_building_with_cache(building_id: str, entity_uuid: str) -> Optional[Building]:
    """
    Smart building retrieval with caching and performance monitoring
    """
    cache_key = CACHE_KEYS["building"].format(entity_uuid=entity_uuid, building_id=building_id)
    
    start_time = time.perf_counter()
    
    # Try cache first with error handling
    try:
        cached_building = await get_cache_fast(cache_key)
        if cached_building is not None:
            if cached_building.get("not_found"):
                return None
                
            cache_time = time.perf_counter() - start_time
            logger.info(f"Cache HIT for building update {building_id} in {cache_time*1000:.2f}ms")
            return Building(**cached_building)
    except Exception as e:
        logger.warning(f"Cache retrieval error for building {building_id}: {e}")
    
    # Cache miss - fetch from database
    db_start = time.perf_counter()
    try:
        building = await Building.find_one({
            "building_id": building_id,
            "entity_uuid": entity_uuid,
            "status": {"$ne": "deleted"}
        })
        
        db_time = time.perf_counter() - db_start
        logger.info(f"Database fetch for building {building_id} took {db_time*1000:.2f}ms")
        
        if building:
            # Cache the building data asynchronously
            building_dict = building.dict()
            asyncio.create_task(
                set_cache_fast(cache_key, building_dict, expire=CACHE_TTL["building"])
            )
        else:
            # Cache negative result
            asyncio.create_task(
                set_cache_fast(cache_key, {"not_found": True}, expire=CACHE_TTL["negative"])
            )
        
        return building
        
    except Exception as e:
        logger.error(f"Database error fetching building {building_id}: {e}")
        return None

async def _check_name_conflict_optimized(name: str, entity_uuid: str, building_id: str) -> bool:
    """
    Optimized name conflict checking with smart caching
    """
    cache_key = CACHE_KEYS["name_check"].format(entity_uuid=entity_uuid, name=name.lower())
    
    start_time = time.perf_counter()
    
    # Try cache first
    try:
        cached_conflict = await get_cache_fast(cache_key)
        if cached_conflict is not None:
            # Check if the conflicting building is different from current one
            conflicting_id = cached_conflict.get('building_id')
            if conflicting_id and conflicting_id != building_id:
                cache_time = time.perf_counter() - start_time
                logger.info(f"Name conflict cache HIT in {cache_time*1000:.2f}ms")
                return True
            return False
    except Exception as e:
        logger.warning(f"Name conflict cache error: {e}")
    
    # Cache miss - check database
    db_start = time.perf_counter()
    try:
        name_conflict = await Building.find_one({
            "name": {"$regex": f"^{name}$", "$options": "i"},  # Case insensitive
            "entity_uuid": entity_uuid,
            "building_id": {"$ne": building_id},
            "status": "active"
        })
        
        db_time = time.perf_counter() - db_start
        logger.info(f"Name conflict DB check took {db_time*1000:.2f}ms")
        
        # Cache the result
        if name_conflict:
            conflict_data = {
                "building_id": name_conflict.building_id, 
                "exists": True,
                "name": name_conflict.name
            }
            asyncio.create_task(
                set_cache_fast(cache_key, conflict_data, expire=CACHE_TTL["name_check"])
            )
            return True
        else:
            no_conflict_data = {"building_id": None, "exists": False}
            asyncio.create_task(
                set_cache_fast(cache_key, no_conflict_data, expire=CACHE_TTL["name_check"])
            )
            return False
            
    except Exception as e:
        logger.error(f"Database error in name conflict check: {e}")
        return False  # Assume no conflict on DB error

async def _invalidate_related_caches_optimized(building_id: str, entity_uuid: str, old_name: str = None, new_name: str = None):
    """
    Optimized cache invalidation with batch operations and wildcard support
    """
    # Core cache keys to invalidate
    cache_keys_to_delete = [
        CACHE_KEYS["building"].format(entity_uuid=entity_uuid, building_id=building_id),
        f"bld_detail:{building_id}",  # From GET API
        CACHE_KEYS["list"].format(entity_uuid=entity_uuid),
        CACHE_KEYS["entity_buildings"].format(entity_uuid=entity_uuid),
        f"buildings:active:{entity_uuid}",
        f"buildings:inactive:{entity_uuid}",
    ]
    
    # Add name-specific caches
    if old_name:
        cache_keys_to_delete.append(
            CACHE_KEYS["name_check"].format(entity_uuid=entity_uuid, name=old_name.lower())
        )
    if new_name:
        cache_keys_to_delete.append(
            CACHE_KEYS["name_check"].format(entity_uuid=entity_uuid, name=new_name.lower())
        )
    
    # Batch delete cache keys (fire and forget)
    async def batch_delete_cache():
        try:
            if cache_keys_to_delete:
                await redis_client.delete(*cache_keys_to_delete)
                logger.info(f"Invalidated {len(cache_keys_to_delete)} cache keys for building {building_id}")
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
    
    # Execute in background
    asyncio.create_task(batch_delete_cache())
    
    # Also clear any result caches that might exist
    try:
        pattern_keys = [
            f"bld_upd:{building_id}:*",
            f"bld_list:{entity_uuid}:*",
        ]
        
        for pattern in pattern_keys:
            asyncio.create_task(_delete_by_pattern(pattern))
    except Exception as e:
        logger.warning(f"Pattern-based cache clearing error: {e}")

async def _delete_by_pattern(pattern: str):
    """Delete cache keys by pattern"""
    try:
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
            logger.debug(f"Deleted {len(keys)} keys matching pattern {pattern}")
    except Exception as e:
        logger.warning(f"Pattern deletion error for {pattern}: {e}")

async def main(
    request: Request,
    building_id: str = Path(..., description="Building ID to update"),
    building_data: BuildingUpdateRequest = None,
    db: AsyncSession = Depends(db)
):
    """
    Optimized building update handler with comprehensive caching
    """
    total_start = time.perf_counter()
    
    # Validate token and get user info
    validate_token_start = time.perf_counter()
    try:
        validate_token(request)
        entity_uuid = request.state.entity_uuid
        user_uuid = request.state.user_uuid
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    validate_token_time = time.perf_counter() - validate_token_start
    logger.info(f"PERF: Token validation took {validate_token_time*1000:.2f}ms")

    try:
        # Get existing building with smart caching
        db_fetch_start = time.perf_counter()
        existing_building = await _get_building_with_cache(building_id, entity_uuid)
        db_fetch_time = time.perf_counter() - db_fetch_start
        logger.info(f"PERF: Building fetch took {db_fetch_time*1000:.2f}ms")
        
        if not existing_building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building with ID '{building_id}' not found"
            )

        # Store old name for cache invalidation
        old_name = existing_building.name

        # Validate input data
        if not building_data or not any([
            building_data.name is not None,
            building_data.address is not None, 
            building_data.description is not None,
            building_data.status is not None
        ]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field must be provided for update"
            )

        # Check name conflict if name is being updated
        new_name = None
        if building_data.name and building_data.name != existing_building.name:
            name_check_start = time.perf_counter()
            has_conflict = await _check_name_conflict_optimized(building_data.name, entity_uuid, building_id)
            name_check_time = time.perf_counter() - name_check_start
            logger.info(f"PERF: Name conflict check took {name_check_time*1000:.2f}ms")
            
            if has_conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Building with name '{building_data.name}' already exists"
                )
            new_name = building_data.name

        # Build update data
        update_data = {}
        if building_data.name is not None:
            update_data["name"] = building_data.name.strip()
        if building_data.address is not None:
            update_data["address"] = building_data.address.strip() if building_data.address else None
        if building_data.description is not None:
            update_data["description"] = building_data.description.strip() if building_data.description else None
        if building_data.status is not None:
            update_data["status"] = building_data.status

        # Add update metadata
        current_time = time.time()
        update_data["update_on"] = current_time
        update_data["updated_by"] = user_uuid

        # Perform database update
        update_start = time.perf_counter()
        try:
            await existing_building.update({"$set": update_data})
            
            # Refresh the building data from database
            updated_building = await Building.find_one({"building_id": building_id})
            if not updated_building:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve updated building data"
                )
                
        except Exception as e:
            logger.error(f"Database update error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update building: {str(e)}"
            )
        
        update_time = time.perf_counter() - update_start
        logger.info(f"PERF: Database update took {update_time*1000:.2f}ms")
        
        # Invalidate related caches after successful update
        await _invalidate_related_caches_optimized(
            building_id, 
            entity_uuid, 
            old_name=old_name if new_name else None,
            new_name=new_name
        )
        
        # Prepare optimized response
        try:
            response = BuildingResponse(
                building_id=updated_building.building_id,
                name=updated_building.name,
                address=getattr(updated_building, 'address', None),
                floors=getattr(updated_building, 'floors', []) or [],
                entity_uuid=updated_building.entity_uuid,
                description=getattr(updated_building, 'description', None),
                datetime=updated_building.datetime,
                update_on=getattr(updated_building, 'update_on', None),
                updated_by=getattr(updated_building, 'updated_by', None),
                status=updated_building.status
            )
        except Exception as e:
            logger.error(f"Response creation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error formatting response data"
            )

        result = {
            "status": "success",
            "message": "Building updated successfully",
            "data": response.dict(),
            "metadata": {
                "updated_fields": list(update_data.keys()),
                "timestamp": current_time
            }
        }

        # Cache the updated building data and result (fire and forget)
        building_cache_key = CACHE_KEYS["building"].format(entity_uuid=entity_uuid, building_id=building_id)
        result_cache_key = CACHE_KEYS["result"].format(building_id=building_id, timestamp=int(current_time))
        
        asyncio.create_task(
            set_cache_fast(building_cache_key, updated_building.dict(), expire=CACHE_TTL["building"])
        )
        asyncio.create_task(
            set_cache_fast(result_cache_key, result, expire=CACHE_TTL["result"])
        )

        # Log comprehensive performance metrics
        total_time = time.perf_counter() - total_start
        logger.info(f"PERF: Building {building_id} updated successfully in {total_time*1000:.2f}ms")
        logger.info(f"PERF: Breakdown - Validation: {validate_token_time*1000:.2f}ms, Fetch: {db_fetch_time*1000:.2f}ms, Update: {update_time*1000:.2f}ms")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error updating building {building_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update building: {str(e)}"
        )
    
    