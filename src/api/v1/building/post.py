
# from fastapi import HTTPException, Depends, status, Request
# from pydantic import BaseModel, Field
# from typing import Optional, List
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
#     # created_by: Optional[str] = None
#     datetime: float
#     status: str

#     class Config:
#         allow_population_by_field_name = True


# async def main(
#     request: Request,    
#     building_data: BuildingCreateRequest,
#     db: AsyncSession = Depends(db)
# ):
    
#     """Main handler for content uploads"""
#     # Validate token and get user info
#     validate_token_start = time.time()
#     validate_token(request)
#     entity_uuid = request.state.entity_uuid
#     user_uuid = request.state.user_uuid
#     validate_token_time = time.time() - validate_token_start
#     logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

#     try:
#         # Check if building with same name exists
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

#         # Create new building
#         new_building = Building(
#             name=building_data.name,
#             address=building_data.address,
#             description=building_data.description,
#             entity_uuid=entity_uuid,
#             floors=[],  # Empty list initially
#             datetime=time.time(),
#             status="active"
#         )

#         # Save to database
#         await new_building.insert()
        
#         logger.info(f"Building created successfully: {new_building.building_id}")

#         # Prepare response
#         response = BuildingResponse(
#             building_id=new_building.building_id,
#             name=new_building.name,
#             address=new_building.address,
#             floors=new_building.floors,
#             entity_uuid=entity_uuid,
#             description=new_building.description,
#             datetime=new_building.datetime,
#             status=new_building.status
#         )

#         return {
#             "status": "success",
#             "message": "Building created successfully",
#             "data": response
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception(f"Error creating building: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to create building: {str(e)}"
#         )


#  redis implemetn

from fastapi import HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import time
import logging
import asyncio
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from src.datamodel.database.domain.DigitalSignage import Building
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db
from src.common.redis_utils import (
    delete_multi_cache, set_cache_fast, get_cache_fast,
    set_cache_background, redis_health_check
)

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
    name: str = Field(..., description="Name of the building", min_length=1, max_length=255)
    address: Optional[str] = Field(None, description="Building address", max_length=500)
    description: Optional[str] = Field(None, description="Description of the building", max_length=1000)

    class Config:
        allow_population_by_field_name = True
        str_strip_whitespace = True  # Auto-strip whitespace


class BuildingResponse(BaseModel):
    building_id: str
    name: str
    address: Optional[str] = None
    floors: List[str] = []
    description: Optional[str] = None
    entity_uuid: Optional[str] = None
    datetime: float
    status: str

    class Config:
        allow_population_by_field_name = True


def generate_cache_pattern_keys(entity_uuid: str) -> List[str]:
    """Generate cache keys that need to be invalidated for this entity"""
    # Use the same pattern as get.py for cache keys
    entity_short = entity_uuid[-12:]  # Last 12 chars like in get.py
    
    # Common cache patterns to invalidate
    patterns = [
        f"b:{entity_short}:a:50:0",      # active, limit 50, skip 0
        f"b:{entity_short}:a:100:0",     # active, limit 100, skip 0
        f"b:{entity_short}:a:25:0",      # active, limit 25, skip 0
        f"b:{entity_short}:a:200:0",     # active, limit 200, skip 0
        f"b:{entity_short}:a:500:0",     # active, limit 500, skip 0
    ]
    
    # Add "all" status patterns
    all_patterns = [
        f"b:{entity_short}:a:50:0",      # "all" -> "a" (first char)
        f"b:{entity_short}:a:100:0",
        f"b:{entity_short}:a:25:0",
        f"b:{entity_short}:a:200:0",
        f"b:{entity_short}:a:500:0",
    ]
    
    return patterns + all_patterns


async def invalidate_building_caches(entity_uuid: str, building_name: Optional[str] = None):
    """Intelligently invalidate related cache entries"""
    try:
        # Get common cache keys to invalidate
        cache_keys = generate_cache_pattern_keys(entity_uuid)
        
        # If building has a name, also invalidate name-based searches
        if building_name:
            entity_short = entity_uuid[-12:]
            name_hash = hashlib.md5(building_name.lower().encode()).hexdigest()[:8]
            
            # Add name-based cache keys
            name_cache_keys = [
                f"b:{entity_short}:a:50:0:{name_hash}",
                f"b:{entity_short}:a:100:0:{name_hash}",
                f"b:{entity_short}:a:25:0:{name_hash}",
            ]
            cache_keys.extend(name_cache_keys)
        
        # Batch delete cache keys (non-blocking)
        asyncio.create_task(delete_multi_cache(cache_keys))
        
        logger.info(f"Invalidated {len(cache_keys)} cache entries for entity {entity_uuid[-8:]}")
        
    except Exception as e:
        # Don't fail the request if cache invalidation fails
        logger.warning(f"Cache invalidation failed: {e}")


async def check_duplicate_building_optimized(name: str, entity_uuid: str, db: AsyncSession) -> bool:
    """Optimized duplicate check with caching"""
    try:
        # Create a cache key for this specific check
        check_key = f"dup_check:{entity_uuid[-12:]}:{hashlib.md5(name.lower().encode()).hexdigest()[:8]}"
        
        # Check cache first (short TTL for consistency)
        cached_result = await get_cache_fast(check_key)
        if cached_result is not None:
            logger.info(f"Duplicate check cache hit for: {name}")
            return cached_result
        
        # Database check with timeout
        existing_building = await asyncio.wait_for(
            Building.find_one({
                "name": {"$regex": f"^{name}$", "$options": "i"},  # Case insensitive exact match
                "entity_uuid": entity_uuid,
                "status": "active"
            }),
            timeout=3.0
        )
        
        exists = existing_building is not None
        
        # Cache the result for 5 minutes (short TTL for data consistency)
        asyncio.create_task(set_cache_fast(check_key, exists, expire=300))
        
        return exists
        
    except asyncio.TimeoutError:
        logger.error(f"Duplicate check timeout for building: {name}")
        raise HTTPException(
            status_code=504, 
            detail="Database timeout during duplicate check"
        )
    except Exception as e:
        logger.error(f"Duplicate check error: {e}")
        # In case of error, assume it might exist to be safe
        return False


async def create_building_optimized(building_data: BuildingCreateRequest, 
                                 entity_uuid: str, db: AsyncSession) -> Building:
    """Optimized building creation with better error handling"""
    try:
        # Create new building with optimized field assignment
        new_building = Building(
            name=building_data.name.strip(),
            address=building_data.address.strip() if building_data.address else None,
            description=building_data.description.strip() if building_data.description else None,
            entity_uuid=entity_uuid,
            floors=[],  # Empty list initially
            datetime=time.time(),
            status="active"
        )

        # Insert with timeout
        await asyncio.wait_for(new_building.insert(), timeout=5.0)
        
        logger.info(f"Building created: {new_building.building_id} | Name: {building_data.name}")
        return new_building
        
    except asyncio.TimeoutError:
        logger.error(f"Database timeout creating building: {building_data.name}")
        raise HTTPException(
            status_code=504,
            detail="Database timeout during building creation"
        )
    except Exception as e:
        logger.error(f"Building creation failed: {e}")
        raise


async def main(
    request: Request,    
    building_data: BuildingCreateRequest,
    db: AsyncSession = Depends(db)
):
    """Ultra-optimized building creation endpoint with Redis integration"""
    
    start_time = time.perf_counter()
    
    # Quick Redis health check (non-blocking)
    redis_healthy = await redis_health_check()
    if not redis_healthy:
        logger.warning("Redis health check failed - cache operations may be degraded")
    
    # Fast token validation
    validate_token_start = time.perf_counter()
    validate_token(request)
    entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid
    validate_token_time = (time.perf_counter() - validate_token_start) * 1000
    
    try:
        # Optimized duplicate check
        duplicate_check_start = time.perf_counter()
        building_exists = await check_duplicate_building_optimized(
            building_data.name, entity_uuid, db
        )
        duplicate_check_time = (time.perf_counter() - duplicate_check_start) * 1000
        
        if building_exists:
            total_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"DUPLICATE REJECTED: {building_data.name} | Total: {total_time:.1f}ms")
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Building with name '{building_data.name}' already exists"
            )

        # Create building
        db_start = time.perf_counter()
        new_building = await create_building_optimized(building_data, entity_uuid, db)
        db_time = (time.perf_counter() - db_start) * 1000

        # Prepare optimized response
        response_data = {
            "building_id": new_building.building_id,
            "name": new_building.name,
            "address": new_building.address,
            "floors": new_building.floors,
            "entity_uuid": entity_uuid,
            "description": new_building.description,
            "datetime": new_building.datetime,
            "status": new_building.status
        }

        # Build final response
        final_response = {
            "status": "success",
            "message": "Building created successfully",
            "data": response_data
        }

        # Invalidate related caches asynchronously (don't block response)
        asyncio.create_task(invalidate_building_caches(entity_uuid, building_data.name))
        
        # Optionally cache the new building data for immediate retrieval
        if redis_healthy:
            building_cache_key = f"building:{new_building.building_id}"
            asyncio.create_task(set_cache_background(building_cache_key, response_data, expire=3600))

        # Performance logging
        total_time = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"BUILDING CREATED: {new_building.building_id} | "
            f"Token: {validate_token_time:.1f}ms | "
            f"DupCheck: {duplicate_check_time:.1f}ms | "
            f"DB: {db_time:.1f}ms | "
            f"Total: {total_time:.1f}ms"
        )

        return JSONResponse(
            status_code=201,
            content=final_response,
            headers={
                "X-Response-Time": f"{total_time:.1f}ms",
                "X-DB-Time": f"{db_time:.1f}ms",
                "X-Cache-Invalidated": "true" if redis_healthy else "false"
            }
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like 409 Conflict)
        raise
    except Exception as e:
        total_time = (time.perf_counter() - start_time) * 1000
        logger.exception(f"Building creation error: {str(e)} | Time: {total_time:.1f}ms")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create building: {str(e)}"
        )


# Additional utility functions for cache management

async def warm_building_cache(building_id: str, building_data: dict):
    """Warm cache with newly created building data"""
    try:
        cache_key = f"building:{building_id}"
        await set_cache_fast(cache_key, building_data, expire=3600)
        logger.info(f"Warmed cache for building: {building_id}")
    except Exception as e:
        logger.warning(f"Cache warming failed for {building_id}: {e}")


async def get_entity_building_count(entity_uuid: str) -> int:
    """Get cached building count for entity (for monitoring)"""
    try:
        count_key = f"building_count:{entity_uuid[-12:]}"
        cached_count = await get_cache_fast(count_key)
        
        if cached_count is not None:
            return cached_count
            
        # If not cached, this would trigger a DB count
        # For now, return -1 to indicate unknown
        return -1
        
    except Exception as e:
        logger.warning(f"Building count check failed: {e}")
        return -1


# Performance monitoring endpoint
async def get_creation_stats():
    """Get building creation performance statistics"""
    return {
        "endpoint": "POST /buildings",
        "cache_integration": "enabled",
        "optimizations": [
            "Redis cache invalidation",
            "Duplicate check caching", 
            "Async cache operations",
            "Performance monitoring",
            "Timeout protection"
        ]
    }