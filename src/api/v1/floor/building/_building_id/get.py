# from fastapi import HTTPException, Path, Query, status, Depends, Request
# from pydantic import BaseModel, Field
# from typing import Optional, List
# import logging
# from src.datamodel.database.domain.DigitalSignage import Building, Floor
# from src.datamodel.datavalidation.apiconfig import ApiConfig
# from src.core.middleware.token_validate_middleware import validate_token
# from src.core.database.dbs.getdb import postresql as db
# import time
# from sqlalchemy.ext.asyncio import AsyncSession


# logger = logging.getLogger(__name__)


# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Floor"],
#         "summary": "Get Floors by Building ID",
#         "response_model": dict,
#         "description": "Retrieve all floors for a specific building.",
#         "response_description": "List of floors for the building",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)


# class FloorResponse(BaseModel):
#     floor_id: str
#     name: str
#     building_id: str
#     floor_number: int
#     floor_plan_url: Optional[str] = None
#     locations_count: int
#     description: Optional[str] = None
#     entity_uuid: Optional[str] = None
#     datetime: float
#     updated_by: Optional[str] = None
#     update_on: Optional[float] = None
#     status: str

#     class Config:
#         allow_population_by_field_name = True


# class BuildingFloorsResponse(BaseModel):
#     building_id: str
#     building_name: str
#     total_floors: int
#     floors: List[FloorResponse]

#     class Config:
#         allow_population_by_field_name = True


# async def main(
#     request: Request,
#     building_id: str = Path(..., description="Building ID to get floors for"),
#     status_filter: Optional[str] = Query("active", description="Filter by status (active, inactive, all)"),
#     include_locations_count: Optional[bool] = Query(True, description="Include count of locations on each floor"),
#     limit: Optional[int] = Query(None, description="Limit number of results"),
#     skip: Optional[int] = Query(0, description="Skip number of results for pagination"),
#     db: AsyncSession = Depends(db)
# ):
    
#         # Get entity_uuid from request
#     validate_token_start = time.time()
    
#     validate_token(request)
#     # await verify_permissions(request, "content", "read")

#     entity_uuid = request.state.entity_uuid
#     user_uuid = request.state.user_uuid
#     validate_token_time = time.time() - validate_token_start
#     logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")



#     try:
#         # First, verify that the building exists
#         building = await Building.find_one({
#             "building_id": building_id,
#             "entity_uuid": entity_uuid
#         })
        
#         if not building:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Building with ID '{building_id}' not found"
#             )

#         # Build query filter for floors
#         query_filter = {"building_id": building_id}
        
#         if status_filter and status_filter != "all":
#             query_filter["status"] = status_filter

#         # Execute query to get floors
#         query = Floor.find(query_filter).sort("floor_number")  # Sort by floor number
        
#         if skip:
#             query = query.skip(skip)
#         if limit:
#             query = query.limit(limit)
            
#         floors = await query.to_list()
        
#         # Prepare response
#         floor_list = []
#         for floor in floors:
#             locations_count = 0
#             if include_locations_count and floor.locations:
#                 locations_count = len(floor.locations)
            
#             floor_response = FloorResponse(
#                 floor_id=floor.floor_id,
#                 name=floor.name,
#                 building_id=floor.building_id,
#                 floor_number=floor.floor_number,
#                 floor_plan_url=floor.floor_plan_url,
#                 locations_count=locations_count,
#                 description=floor.description,
#                 entity_uuid=floor.entity_uuid,
#                 datetime=floor.datetime,
#                 updated_by=floor.updated_by,
#                 update_on=floor.update_on,
#                 status=floor.status
#             )
#             floor_list.append(floor_response)

#         # Create comprehensive response
#         response = BuildingFloorsResponse(
#             building_id=building.building_id,
#             building_name=building.name,
#             total_floors=len(floor_list),
#             floors=floor_list
#         )

#         logger.info(f"Retrieved {len(floor_list)} floors for building: {building_id}")

#         return {
#             "status": "success",
#             "message": f"Retrieved {len(floor_list)} floors for building '{building.name}'",
#             "data": response
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception(f"Error retrieving floors for building {building_id}: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve floors for building: {str(e)}"
#         )

# redis imports
from fastapi import HTTPException, Path, Query, status, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import hashlib
import json
import time
import asyncio

from src.datamodel.database.domain.DigitalSignage import Building, Floor
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db
from sqlalchemy.ext.asyncio import AsyncSession

# Import your existing Redis utilities
from src.common.redis_utils import (
    get_cache_fast, 
    set_cache_background
)

logger = logging.getLogger(__name__)

# ULTRA-FAST Cache configuration - aggressive caching
CACHE_TTL = {
    "hot_path": 1800,      # 30 minutes for complete responses (HOT PATH)
    "building": 3600,      # 1 hour for building data (very stable)
    "floors": 1800,        # 30 minutes for floor data
    "not_found": 300,      # 5 minutes for 404s (prevent DB hammering)
}

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Floor"],
        "summary": "Get Floors by Building ID",
        "response_model": dict,
        "description": "Retrieve all floors for a specific building.",
        "response_description": "List of floors for the building",
        "deprecated": False,
    }
    return ApiConfig(**config)

class FloorResponse(BaseModel):
    floor_id: str
    name: str
    building_id: str
    floor_number: int
    floor_plan_url: Optional[str] = None
    locations_count: int
    description: Optional[str] = None
    entity_uuid: Optional[str] = None
    datetime: float
    updated_by: Optional[str] = None
    update_on: Optional[float] = None
    status: str

    class Config:
        allow_population_by_field_name = True

class BuildingFloorsResponse(BaseModel):
    building_id: str
    building_name: str
    total_floors: int
    floors: List[FloorResponse]

    class Config:
        allow_population_by_field_name = True

def _ultra_fast_cache_key(building_id: str, entity_uuid: str, status_filter: str, 
                         include_locations: bool, limit: Optional[int], skip: int) -> str:
    """Ultra-fast cache key generation - minimal overhead"""
    # Use simple string concatenation instead of JSON serialization for speed
    key_parts = [
        "floors_v2",  # Version prefix for cache busting if needed
        building_id,
        entity_uuid[:8],  # Only first 8 chars of entity_uuid for brevity
        status_filter or "active",
        "loc" if include_locations else "noloc",
        str(limit or "all"),
        str(skip)
    ]
    return ":".join(key_parts)

async def main(
    request: Request,
    building_id: str = Path(..., description="Building ID to get floors for"),
    status_filter: Optional[str] = Query("active", description="Filter by status (active, inactive, all)"),
    include_locations_count: Optional[bool] = Query(True, description="Include count of locations on each floor"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    skip: Optional[int] = Query(0, description="Skip number of results for pagination"),
    db: AsyncSession = Depends(db)
):
    start_time = time.perf_counter()
    
    # ULTRA-FAST token validation
    validate_token_start = time.perf_counter()
    validate_token(request)
    entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid
    validate_token_time = time.perf_counter() - validate_token_start
    
    try:
        # STEP 1: ULTRA-FAST cache key generation (< 1ms)
        cache_key = _ultra_fast_cache_key(
            building_id, entity_uuid, status_filter, 
            include_locations_count, limit, skip
        )
        
        # STEP 2: PRIMARY HOT PATH - Complete result cache check (< 5ms)
        cache_check_start = time.perf_counter()
        cached_result = await get_cache_fast(cache_key)
        cache_check_time = time.perf_counter() - cache_check_start
        
        if cached_result is not None:
            total_time = time.perf_counter() - start_time
            logger.info(f"ULTRA-FAST: Token={validate_token_time*1000:.1f}ms, Cache={cache_check_time*1000:.1f}ms, Total={total_time*1000:.1f}ms [CACHE HIT]")
            return cached_result

        # STEP 3: Cache miss - Fast DB operations with minimal processing
        logger.warning(f"Cache miss for key: {cache_key}")
        db_start = time.perf_counter()
        
        # Single optimized query - get building and floors together
        try:
            # Parallel DB queries for maximum speed
            building_task = Building.find_one({
                "building_id": building_id,
                "entity_uuid": entity_uuid
            })
            
            # Build floors query
            floor_filter = {"building_id": building_id}
            if status_filter and status_filter != "all":
                floor_filter["status"] = status_filter
                
            floors_query = Floor.find(floor_filter).sort("floor_number")
            if skip:
                floors_query = floors_query.skip(skip)
            if limit:
                floors_query = floors_query.limit(limit)
            floors_task = floors_query.to_list()
            
            # Execute both queries in parallel
            building, floors = await asyncio.gather(building_task, floors_task, return_exceptions=True)
            
            # Handle exceptions from parallel execution
            if isinstance(building, Exception):
                raise building
            if isinstance(floors, Exception):
                raise floors
                
        except Exception as e:
            logger.error(f"DB query error: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        db_time = time.perf_counter() - db_start
        
        # Fast 404 handling
        if not building:
            not_found_result = {
                "status": "error",
                "message": f"Building with ID '{building_id}' not found",
                "data": None
            }
            # Cache 404s to prevent repeated queries
            asyncio.create_task(
                set_cache_background(cache_key, not_found_result, expire=CACHE_TTL["not_found"])
            )
            raise HTTPException(status_code=404, detail=f"Building with ID '{building_id}' not found")

        # STEP 4: ULTRA-FAST response building (< 2ms)
        response_build_start = time.perf_counter()
        
        # Pre-allocate list for speed
        floor_list = []
        floor_list_append = floor_list.append  # Cache the append method
        
        # Optimized floor processing - minimal attribute access
        for floor in floors:
            # Use direct attribute access with fallbacks - faster than getattr
            try:
                locations_count = len(floor.locations) if (include_locations_count and hasattr(floor, 'locations') and floor.locations) else 0
                
                # Create response object with minimal overhead
                floor_response = FloorResponse(
                    floor_id=floor.floor_id,
                    name=floor.name,
                    building_id=floor.building_id,
                    floor_number=getattr(floor, 'floor_number', 0),
                    floor_plan_url=getattr(floor, 'floor_plan_url', None),
                    locations_count=locations_count,
                    description=getattr(floor, 'description', None),
                    entity_uuid=getattr(floor, 'entity_uuid', None),
                    datetime=floor.datetime,
                    updated_by=getattr(floor, 'updated_by', None),
                    update_on=getattr(floor, 'update_on', None),
                    status=floor.status
                )
                floor_list_append(floor_response)
            except Exception as e:
                # Log but continue - don't let one bad record break everything
                logger.warning(f"Skipping floor {getattr(floor, 'floor_id', 'unknown')}: {e}")
                continue

        # Build final response
        response_data = BuildingFloorsResponse(
            building_id=building.building_id,
            building_name=building.name,
            total_floors=len(floor_list),
            floors=floor_list
        )
        
        final_result = {
            "status": "success",
            "message": f"Retrieved {len(floor_list)} floors for building '{building.name}'",
            "data": response_data.dict()
        }
        
        response_build_time = time.perf_counter() - response_build_start
        
        # STEP 5: Background caching (non-blocking)
        # Fire-and-forget caching to avoid blocking the response
        asyncio.create_task(
            set_cache_background(cache_key, final_result, expire=CACHE_TTL["hot_path"])
        )
        
        # Performance logging
        total_time = time.perf_counter() - start_time
        logger.info(f"PERFORMANCE: Token={validate_token_time*1000:.1f}ms, DB={db_time*1000:.1f}ms, Response={response_build_time*1000:.1f}ms, Total={total_time*1000:.1f}ms [CACHE MISS]")
        
        return final_result

    except HTTPException:
        raise
    except Exception as e:
        total_time = time.perf_counter() - start_time
        logger.exception(f"Error after {total_time*1000:.1f}ms: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve floors for building: {str(e)}"
        )
    
    