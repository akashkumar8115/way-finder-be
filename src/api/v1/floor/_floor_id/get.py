# from fastapi import HTTPException, Path, status
# from pydantic import BaseModel, Field
# from typing import Optional, List
# import logging
# from src.datamodel.database.domain.DigitalSignage import Floor, Location
# from src.datamodel.datavalidation.apiconfig import ApiConfig


# logger = logging.getLogger(__name__)


# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Floor"],
#         "summary": "Get Floor by ID",
#         "response_model": dict,
#         "description": "Retrieve a specific floor by its ID with detailed location information.",
#         "response_description": "Floor details with locations",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)


# class LocationDetailResponse(BaseModel):
#     location_id: str
#     name: str
#     category: str
#     shape: str
#     x: float
#     y: float
#     width: Optional[float] = None
#     height: Optional[float] = None
#     radius: Optional[float] = None
#     logo_url: Optional[str] = None
#     description: Optional[str] = None
#     status: str

#     class Config:
#         allow_population_by_field_name = True


# class FloorDetailResponse(BaseModel):
#     floor_id: str
#     name: str
#     building_id: Optional[str] = None
#     floor_number: int
#     floor_plan_url: Optional[str] = None
#     locations: List[LocationDetailResponse] = []
#     description: Optional[str] = None
#     created_by: Optional[str] = None
#     datetime: float
#     updated_by: Optional[str] = None
#     update_on: Optional[float] = None
#     status: str

#     class Config:
#         allow_population_by_field_name = True


# async def main(
#     floor_id: str = Path(..., description="Floor ID to retrieve")
# ):
#     try:
#         # Find floor by ID
#         floor = await Floor.find_one({
#             "floor_id": floor_id
#         })
        
#         if not floor:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Floor with ID '{floor_id}' not found"
#             )

#         # Get detailed location information
#         location_details = []
#         if floor.locations:
#             locations = await Location.find({
#                 "location_id": {"$in": floor.locations},
#                 "status": "active"
#             }).to_list()
            
#             for location in locations:
#                 location_detail = LocationDetailResponse(
#                     location_id=location.location_id,
#                     name=location.name,
#                     category=location.category,
#                     shape=location.shape.value,
#                     x=location.x,
#                     y=location.y,
#                     width=location.width,
#                     height=location.height,
#                     radius=location.radius,
#                     logo_url=location.logo_url,
#                     description=location.description,
#                     status=location.status
#                 )
#                 location_details.append(location_detail)

#         # Prepare response
#         response = FloorDetailResponse(
#             floor_id=floor.floor_id,
#             name=floor.name,
#             building_id=floor.building_id,
#             floor_number=floor.floor_number,
#             floor_plan_url=floor.floor_plan_url,
#             locations=location_details,
#             description=floor.description,
#             created_by=floor.created_by,
#             datetime=floor.datetime,
#             updated_by=floor.updated_by,
#             update_on=floor.update_on,
#             status=floor.status
#         )

#         logger.info(f"Retrieved floor details: {floor_id}")

#         return {
#             "status": "success",
#             "message": "Floor retrieved successfully",
#             "data": response
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception(f"Error retrieving floor: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve floor: {str(e)}"
#         )



from fastapi import HTTPException, Path, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import time
import asyncio

from src.datamodel.database.domain.DigitalSignage import Floor, Location
from src.datamodel.datavalidation.apiconfig import ApiConfig

# Import your existing Redis utilities
from src.common.redis_utils import (
    get_cache_fast, 
    set_cache_background
)

logger = logging.getLogger(__name__)

# ULTRA-AGGRESSIVE Cache configuration for maximum speed
CACHE_TTL = {
    "hot_path": 2700,      # 45 minutes for complete responses (ULTRA HOT PATH)
    "floor": 3600,         # 1 hour for floor data (very stable)
    "locations": 1800,     # 30 minutes for location data
    "not_found": 300,      # 5 minutes for 404s
}

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Floor"],
        "summary": "Get Floor by ID",
        "response_model": dict,
        "description": "Retrieve a specific floor by its ID with detailed location information.",
        "response_description": "Floor details with locations",
        "deprecated": False,
    }
    return ApiConfig(**config)

class LocationDetailResponse(BaseModel):
    location_id: str
    name: str
    category: str
    shape: str
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    status: str

    class Config:
        allow_population_by_field_name = True

class FloorDetailResponse(BaseModel):
    floor_id: str
    name: str
    building_id: Optional[str] = None
    floor_number: int
    floor_plan_url: Optional[str] = None
    locations: List[LocationDetailResponse] = []
    description: Optional[str] = None
    created_by: Optional[str] = None
    datetime: float
    updated_by: Optional[str] = None
    update_on: Optional[float] = None
    status: str

    class Config:
        allow_population_by_field_name = True

def _ultra_fast_cache_key(floor_id: str) -> str:
    """Ultra-fast cache key generation - minimal overhead"""
    return f"floor_detail_v2:{floor_id}"

async def main(
    floor_id: str = Path(..., description="Floor ID to retrieve")
):
    start_time = time.perf_counter()
    
    try:
        # STEP 1: ULTRA-FAST cache key generation (< 0.1ms)
        cache_key = _ultra_fast_cache_key(floor_id)
        
        # STEP 2: PRIMARY HOT PATH - Complete result cache check (< 5ms)
        cache_check_start = time.perf_counter()
        cached_result = await get_cache_fast(cache_key)
        cache_check_time = time.perf_counter() - cache_check_start
        
        if cached_result is not None:
            total_time = time.perf_counter() - start_time
            logger.info(f"ULTRA-FAST FLOOR: Cache={cache_check_time*1000:.1f}ms, Total={total_time*1000:.1f}ms [CACHE HIT]")
            return cached_result

        # STEP 3: Cache miss - Maximum speed DB operations
        logger.warning(f"Cache miss for floor: {floor_id}")
        db_start = time.perf_counter()
        
        try:
            # Find floor first
            floor = await Floor.find_one({"floor_id": floor_id})
            
            if not floor:
                # Fast 404 handling with caching
                not_found_result = {
                    "status": "error",
                    "message": f"Floor with ID '{floor_id}' not found",
                    "data": None
                }
                asyncio.create_task(
                    set_cache_background(cache_key, not_found_result, expire=CACHE_TTL["not_found"])
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Floor with ID '{floor_id}' not found"
                )

            # Get locations in parallel if floor has locations
            locations = []
            if hasattr(floor, 'locations') and floor.locations:
                try:
                    locations = await Location.find({
                        "location_id": {"$in": floor.locations},
                        "status": "active"
                    }).to_list()
                except Exception as e:
                    logger.warning(f"Error fetching locations for floor {floor_id}: {e}")
                    # Continue with empty locations rather than failing
                    locations = []
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"DB query error for floor {floor_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        db_time = time.perf_counter() - db_start

        # STEP 4: ULTRA-FAST response building (< 2ms)
        response_build_start = time.perf_counter()
        
        # Build location details with minimal overhead
        location_details = []
        location_details_append = location_details.append  # Cache the append method
        
        for location in locations:
            try:
                # Handle enum values safely and efficiently
                category_val = getattr(location.category, 'value', str(location.category))
                shape_val = getattr(location.shape, 'value', str(location.shape))
                
                location_detail = LocationDetailResponse(
                    location_id=location.location_id,
                    name=location.name,
                    category=category_val,
                    shape=shape_val,
                    x=location.x,
                    y=location.y,
                    width=getattr(location, 'width', None),
                    height=getattr(location, 'height', None),
                    radius=getattr(location, 'radius', None),
                    logo_url=getattr(location, 'logo_url', None),
                    description=getattr(location, 'description', None),
                    status=location.status
                )
                location_details_append(location_detail)
            except Exception as e:
                logger.warning(f"Skipping location {getattr(location, 'location_id', 'unknown')}: {e}")
                continue

        # Build floor response with safe attribute access
        try:
            response = FloorDetailResponse(
                floor_id=floor.floor_id,
                name=floor.name,
                building_id=getattr(floor, 'building_id', None),
                floor_number=getattr(floor, 'floor_number', 0),
                floor_plan_url=getattr(floor, 'floor_plan_url', None),
                locations=location_details,
                description=getattr(floor, 'description', None),
                created_by=getattr(floor, 'created_by', None),
                datetime=floor.datetime,
                updated_by=getattr(floor, 'updated_by', None),
                update_on=getattr(floor, 'update_on', None),
                status=floor.status
            )
        except Exception as e:
            logger.error(f"Error creating FloorDetailResponse: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing floor data"
            )

        # Build final result
        final_result = {
            "status": "success",
            "message": "Floor retrieved successfully",
            "data": response.dict()  # Convert to dict for caching
        }
        
        response_build_time = time.perf_counter() - response_build_start
        
        # STEP 5: Background caching (non-blocking)
        asyncio.create_task(
            set_cache_background(cache_key, final_result, expire=CACHE_TTL["hot_path"])
        )
        
        # Performance logging
        total_time = time.perf_counter() - start_time
        logger.info(f"FLOOR PERFORMANCE: DB={db_time*1000:.1f}ms, Response={response_build_time*1000:.1f}ms, Total={total_time*1000:.1f}ms [MISS] - {len(location_details)} locations")
        
        return final_result

    except HTTPException:
        raise
    except Exception as e:
        total_time = time.perf_counter() - start_time
        logger.exception(f"Floor error after {total_time*1000:.1f}ms: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve floor: {str(e)}"
        )