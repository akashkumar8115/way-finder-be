from fastapi import HTTPException, Query, status, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from src.datamodel.database.domain.DigitalSignage import Floor
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db
import time
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Floor"],
        "summary": "Get Floors",
        "response_model": dict,
        "description": "Retrieve all floors or filter by building ID and other criteria.",
        "response_description": "List of floors",
        "deprecated": False,
    }
    return ApiConfig(**config)


class FloorResponse(BaseModel):
    floor_id: str
    name: str
    building_id: Optional[str] = None
    floor_number: int
    floor_plan_url: Optional[str] = None
    locations: List[str] = []
    description: Optional[str] = None
    entity_uuid: Optional[str] = None
    datetime: float
    updated_by: Optional[str] = None
    update_on: Optional[float] = None
    status: str

    class Config:
        allow_population_by_field_name = True


async def main(
    request: Request,    
    building_id: Optional[str] = Query(None, description="Filter by building ID"),
    status_filter: Optional[str] = Query("active", description="Filter by status (active, inactive, all)"),
    name: Optional[str] = Query(None, description="Filter by floor name (partial match)"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    skip: Optional[int] = Query(0, description="Skip number of results for pagination"),
    db: AsyncSession = Depends(db)
):
    

    # Get entity_uuid from request
    validate_token_start = time.time()
    
    validate_token(request)
    # await verify_permissions(request, "content", "read")

    entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")


    try:
        # Build query filter
        query_filter = {"entity_uuid": entity_uuid}  # Filter by entity UUID
        
        if building_id:
            query_filter["building_id"] = building_id
            
        if status_filter and status_filter != "all":
            query_filter["status"] = status_filter
        
        if name:
            query_filter["name"] = {"$regex": name, "$options": "i"}  # Case-insensitive partial match

        # Execute query
        query = Floor.find(query_filter).sort("floor_number")  # Sort by floor number
        
        if skip:
            query = query.skip(skip)
        if limit:
            query = query.limit(limit)
            
        floors = await query.to_list()
        
        # Prepare response
        floor_list = []
        for floor in floors:
            floor_response = FloorResponse(
                floor_id=floor.floor_id,
                name=floor.name,
                building_id=floor.building_id,
                floor_number=floor.floor_number,
                floor_plan_url=floor.floor_plan_url,
                locations=floor.locations or [],
                description=floor.description,
                entity_uuid=floor.entity_uuid,
                datetime=floor.datetime,
                updated_by=floor.updated_by,
                update_on=floor.update_on,
                status=floor.status
            )
            floor_list.append(floor_response)

        logger.info(f"Retrieved {len(floor_list)} floors")

        return {
            "status": "success",
            "message": f"Retrieved {len(floor_list)} floors",
            "data": floor_list,
            "total": len(floor_list)
        }

    except Exception as e:
        logger.exception(f"Error retrieving floors: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve floors: {str(e)}"
        )


# from fastapi import HTTPException, Query, status, Depends, Request
# from pydantic import BaseModel, Field
# from typing import Optional, List
# import logging
# import hashlib
# import json
# import time
# import asyncio

# from src.datamodel.database.domain.DigitalSignage import Floor
# from src.datamodel.datavalidation.apiconfig import ApiConfig
# from src.core.middleware.token_validate_middleware import validate_token
# from src.core.database.dbs.getdb import postresql as db
# from sqlalchemy.ext.asyncio import AsyncSession

# # Import your existing Redis utilities
# from src.common.redis_utils import (
#     get_cache_fast, 
#     set_cache_background
# )

# logger = logging.getLogger(__name__)

# # ULTRA-AGGRESSIVE Cache configuration for maximum speed
# CACHE_TTL = {
#     "hot_path": 1800,      # 30 minutes for complete responses
#     "user_specific": 900,  # 15 minutes for entity-specific results
#     "not_found": 300,      # 5 minutes for empty results
# }

# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Floor"],
#         "summary": "Get Floors",
#         "response_model": dict,
#         "description": "Retrieve all floors or filter by building ID and other criteria.",
#         "response_description": "List of floors",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)

# class FloorResponse(BaseModel):
#     floor_id: str
#     name: str
#     building_id: Optional[str] = None
#     floor_number: int
#     floor_plan_url: Optional[str] = None
#     locations: List[str] = []
#     description: Optional[str] = None
#     entity_uuid: Optional[str] = None
#     datetime: float
#     updated_by: Optional[str] = None
#     update_on: Optional[float] = None
#     status: str

#     class Config:
#         allow_population_by_field_name = True

# def _ultra_fast_cache_key(entity_uuid: str, building_id: Optional[str], status_filter: str, 
#                          name: Optional[str], limit: Optional[int], skip: int) -> str:
#     """Ultra-fast cache key generation with minimal overhead"""
#     # Use simple string concatenation for maximum speed
#     key_parts = [
#         "floors_list_v2",  # Version prefix
#         entity_uuid[:8],   # First 8 chars of entity_uuid for brevity
#         building_id or "all",
#         status_filter or "active",
#         name or "all",
#         str(limit or "all"),
#         str(skip)
#     ]
#     return ":".join(key_parts)

# async def main(
#     request: Request,    
#     building_id: Optional[str] = Query(None, description="Filter by building ID"),
#     status_filter: Optional[str] = Query("active", description="Filter by status (active, inactive, all)"),
#     name: Optional[str] = Query(None, description="Filter by floor name (partial match)"),
#     limit: Optional[int] = Query(None, description="Limit number of results"),
#     skip: Optional[int] = Query(0, description="Skip number of results for pagination"),
#     db: AsyncSession = Depends(db)
# ):
#     start_time = time.perf_counter()
    
#     # ULTRA-FAST token validation
#     validate_token_start = time.perf_counter()
#     validate_token(request)
#     entity_uuid = request.state.entity_uuid
#     user_uuid = request.state.user_uuid
#     validate_token_time = time.perf_counter() - validate_token_start

#     try:
#         # STEP 1: ULTRA-FAST cache key generation (< 0.5ms)
#         cache_key = _ultra_fast_cache_key(
#             entity_uuid, building_id, status_filter, name, limit, skip
#         )
        
#         # STEP 2: PRIMARY HOT PATH - Complete result cache check (< 5ms)
#         cache_check_start = time.perf_counter()
#         cached_result = await get_cache_fast(cache_key)
#         cache_check_time = time.perf_counter() - cache_check_start
        
#         if cached_result is not None:
#             total_time = time.perf_counter() - start_time
#             logger.info(f"ULTRA-FAST FLOORS LIST: Token={validate_token_time*1000:.1f}ms, Cache={cache_check_time*1000:.1f}ms, Total={total_time*1000:.1f}ms [CACHE HIT]")
#             return cached_result

#         # STEP 3: Cache miss - Fast DB operations
#         logger.warning(f"Cache miss for floors list: {cache_key}")
#         db_start = time.perf_counter()
        
#         try:
#             # Build query filter
#             query_filter = {"entity_uuid": entity_uuid}  # Filter by entity UUID
            
#             if building_id:
#                 query_filter["building_id"] = building_id
                
#             if status_filter and status_filter != "all":
#                 query_filter["status"] = status_filter
            
#             if name:
#                 query_filter["name"] = {"$regex": name, "$options": "i"}  # Case-insensitive partial match

#             # Execute optimized query with pagination
#             query = Floor.find(query_filter).sort("floor_number")  # Sort by floor number
            
#             if skip:
#                 query = query.skip(skip)
#             if limit:
#                 query = query.limit(limit)
                
#             floors = await query.to_list()
            
#         except Exception as e:
#             logger.error(f"DB query error: {e}")
#             raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
#         db_time = time.perf_counter() - db_start

#         # STEP 4: ULTRA-FAST response building (< 3ms)
#         response_build_start = time.perf_counter()
        
#         # Build response with minimal overhead
#         floor_list = []
#         floor_list_append = floor_list.append  # Cache the append method
        
#         for floor in floors:
#             try:
#                 floor_response = FloorResponse(
#                     floor_id=floor.floor_id,
#                     name=floor.name,
#                     building_id=getattr(floor, 'building_id', None),
#                     floor_number=getattr(floor, 'floor_number', 0),
#                     floor_plan_url=getattr(floor, 'floor_plan_url', None),
#                     locations=getattr(floor, 'locations', []) or [],
#                     description=getattr(floor, 'description', None),
#                     entity_uuid=getattr(floor, 'entity_uuid', None),
#                     datetime=floor.datetime,
#                     updated_by=getattr(floor, 'updated_by', None),
#                     update_on=getattr(floor, 'update_on', None),
#                     status=floor.status
#                 )
#                 floor_list_append(floor_response)
#             except Exception as e:
#                 logger.warning(f"Skipping floor {getattr(floor, 'floor_id', 'unknown')}: {e}")
#                 continue

#         # Build final result
#         final_result = {
#             "status": "success",
#             "message": f"Retrieved {len(floor_list)} floors",
#             "data": [floor.dict() for floor in floor_list],  # Convert to dict for caching
#             "total": len(floor_list)
#         }
        
#         response_build_time = time.perf_counter() - response_build_start
        
#         # STEP 5: Background caching (non-blocking)
#         # Use shorter TTL for user-specific data
#         cache_ttl = CACHE_TTL["user_specific"] if entity_uuid else CACHE_TTL["hot_path"]
        
#         # Cache empty results too, but for shorter duration
#         if len(floor_list) == 0:
#             cache_ttl = CACHE_TTL["not_found"]
        
#         asyncio.create_task(
#             set_cache_background(cache_key, final_result, expire=cache_ttl)
#         )
        
#         # Performance logging
#         total_time = time.perf_counter() - start_time
#         logger.info(f"FLOORS LIST PERFORMANCE: Token={validate_token_time*1000:.1f}ms, DB={db_time*1000:.1f}ms, Response={response_build_time*1000:.1f}ms, Total={total_time*1000:.1f}ms [MISS] - {len(floor_list)} floors")
        
#         return final_result

#     except HTTPException:
#         raise
#     except Exception as e:
#         total_time = time.perf_counter() - start_time
#         logger.exception(f"Floors list error after {total_time*1000:.1f}ms: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve floors: {str(e)}"
#         )