# from fastapi import HTTPException, Query, Path, status
# from pydantic import BaseModel, Field
# from typing import Optional, List
# import logging
# from src.datamodel.database.domain.DigitalSignage import Location, Floor, Building, LocationType, ShapeType
# from src.datamodel.datavalidation.apiconfig import ApiConfig

# logger = logging.getLogger(__name__)


# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Location"],
#         "summary": "Get All Locations by Building ID",
#         "response_model": dict,
#         "description": "Retrieve all locations within a specific building, organized by floors.",
#         "response_description": "List of locations grouped by floors",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)


# class LocationItem(BaseModel):
#     location_id: str
#     name: str
#     category: str
#     floor_id: str
#     shape: str
#     x: float
#     y: float
#     width: Optional[float] = None
#     height: Optional[float] = None
#     radius: Optional[float] = None
#     logo_url: Optional[str] = Field(None, alias="logoUrl")
#     color: str
#     text_color: str
#     is_published: bool
#     description: Optional[str] = None
#     created_by: Optional[str] = None
#     datetime: float
#     status: str

#     class Config:
#         allow_population_by_field_name = True


# class FloorWithLocations(BaseModel):
#     floor_id: str
#     floor_name: str
#     floor_number: int
#     floor_plan_url: Optional[str] = None
#     locations: List[LocationItem] = []
#     total_locations: int = 0

#     class Config:
#         allow_population_by_field_name = True


# class LocationsResponse(BaseModel):
#     building_id: str
#     building_name: str
#     floors: List[FloorWithLocations] = []
#     total_floors: int = 0
#     total_locations: int = 0


# async def main(
#     building_id: str = Path(..., description="Building ID to get locations for"),
#     floor_id: Optional[str] = Query(None, description="Optional floor ID to filter locations"),
#     category: Optional[LocationType] = Query(None, description="Optional category filter"),
#     is_published: Optional[bool] = Query(None, description="Filter by published status"),
#     include_inactive: bool = Query(False, description="Include inactive locations")
# ):
#     try:
#         # Validate building exists
#         building = await Building.find_one({
#             "building_id": building_id,
#             "status": "active"
#         })
        
#         if not building:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Building with ID '{building_id}' not found"
#             )

#         # Build location filter
#         location_filter = {
#             "status": {"$in": ["active", "inactive"] if include_inactive else ["active"]}
#         }
        
#         if category:
#             location_filter["category"] = category
            
#         if is_published is not None:
#             location_filter["is_published"] = is_published

#         # Get floors for the building
#         floor_filter = {
#             "building_id": building_id,
#             "status": "active"
#         }
        
#         if floor_id:
#             floor_filter["floor_id"] = floor_id
            
#         floors = await Floor.find(floor_filter).sort("floor_number").to_list()
        
#         if not floors:
#             return {
#                 "status": "success",
#                 "message": "No floors found for this building",
#                 "data": LocationsResponse(
#                     building_id=building_id,
#                     building_name=building.name,
#                     floors=[],
#                     total_floors=0,
#                     total_locations=0
#                 )
#             }

#         floors_with_locations = []
#         total_locations = 0

#         # Get locations for each floor
#         for floor in floors:
#             # Add floor_id to location filter
#             floor_location_filter = {**location_filter, "floor_id": floor.floor_id}
            
#             # Get locations for this floor
#             locations = await Location.find(floor_location_filter).to_list()
            
#             # Convert locations to response format
#             location_items = []
#             for location in locations:
#                 location_item = LocationItem(
#                     location_id=location.location_id,
#                     name=location.name,
#                     category=location.category.value,
#                     floor_id=location.floor_id,
#                     shape=location.shape.value,
#                     x=location.x,
#                     y=location.y,
#                     width=location.width,
#                     height=location.height,
#                     radius=location.radius,
#                     logo_url=location.logo_url,
#                     color=location.color,
#                     text_color=location.text_color,
#                     is_published=location.is_published,
#                     description=location.description,
#                     created_by=location.created_by,
#                     datetime=location.datetime,
#                     status=location.status
#                 )
#                 location_items.append(location_item)

#             # Create floor with locations
#             floor_with_locations = FloorWithLocations(
#                 floor_id=floor.floor_id,
#                 floor_name=floor.name,
#                 floor_number=floor.floor_number,
#                 floor_plan_url=floor.floor_plan_url,
#                 locations=location_items,
#                 total_locations=len(location_items)
#             )
            
#             floors_with_locations.append(floor_with_locations)
#             total_locations += len(location_items)

#         # Prepare response
#         response = LocationsResponse(
#             building_id=building_id,
#             building_name=building.name,
#             floors=floors_with_locations,
#             total_floors=len(floors_with_locations),
#             total_locations=total_locations
#         )

#         logger.info(f"Retrieved {total_locations} locations across {len(floors_with_locations)} floors for building: {building_id}")

#         return {
#             "status": "success",
#             "message": f"Retrieved locations for building '{building.name}'",
#             "data": response
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception(f"Error retrieving locations for building {building_id}: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve locations: {str(e)}"
#         )

from fastapi import HTTPException, Query, Path, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import time
import asyncio

from src.datamodel.database.domain.DigitalSignage import Location, Floor, Building, LocationType, ShapeType
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
    "building": 3600,      # 1 hour for building data
    "floors": 2700,        # 45 minutes for floor data
    "locations": 1800,     # 30 minutes for location data
    "not_found": 300,      # 5 minutes for 404s
}

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Location"],
        "summary": "Get All Locations by Building ID",
        "response_model": dict,
        "description": "Retrieve all locations within a specific building, organized by floors.",
        "response_description": "List of locations grouped by floors",
        "deprecated": False,
    }
    return ApiConfig(**config)

class LocationItem(BaseModel):
    location_id: str
    name: str
    category: str
    floor_id: str
    shape: str
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None
    logo_url: Optional[str] = Field(None, alias="logoUrl")
    color: str
    text_color: str
    is_published: bool
    description: Optional[str] = None
    created_by: Optional[str] = None
    datetime: float
    status: str

    class Config:
        allow_population_by_field_name = True

class FloorWithLocations(BaseModel):
    floor_id: str
    floor_name: str
    floor_number: int
    floor_plan_url: Optional[str] = None
    locations: List[LocationItem] = []
    total_locations: int = 0

    class Config:
        allow_population_by_field_name = True

class LocationsResponse(BaseModel):
    building_id: str
    building_name: str
    floors: List[FloorWithLocations] = []
    total_floors: int = 0
    total_locations: int = 0

def _ultra_fast_cache_key(building_id: str, floor_id: Optional[str], category: Optional[str], 
                         is_published: Optional[bool], include_inactive: bool) -> str:
    """Ultra-fast cache key generation with minimal string operations"""
    # Use simple concatenation for maximum speed
    key_parts = [
        "locations_v3",  # Version prefix
        building_id,
        floor_id or "all",
        str(category) if category else "all",
        "pub" if is_published is True else "unpub" if is_published is False else "all",
        "inc" if include_inactive else "act"
    ]
    return ":".join(key_parts)

async def main(
    building_id: str = Path(..., description="Building ID to get locations for"),
    floor_id: Optional[str] = Query(None, description="Optional floor ID to filter locations"),
    category: Optional[LocationType] = Query(None, description="Optional category filter"),
    is_published: Optional[bool] = Query(None, description="Filter by published status"),
    include_inactive: bool = Query(False, description="Include inactive locations")
):
    start_time = time.perf_counter()
    
    try:
        # STEP 1: ULTRA-FAST cache key generation (< 0.5ms)
        cache_key = _ultra_fast_cache_key(
            building_id, floor_id, str(category) if category else None, 
            is_published, include_inactive
        )
        
        # STEP 2: PRIMARY HOT PATH - Complete result cache check (< 5ms)
        cache_check_start = time.perf_counter()
        cached_result = await get_cache_fast(cache_key)
        cache_check_time = time.perf_counter() - cache_check_start
        
        if cached_result is not None:
            total_time = time.perf_counter() - start_time
            logger.info(f"ULTRA-FAST LOCATIONS: Cache={cache_check_time*1000:.1f}ms, Total={total_time*1000:.1f}ms [CACHE HIT] 🚀")
            return cached_result

        # STEP 3: Cache miss - Maximum speed DB operations
        logger.warning(f"Cache miss for locations key: {cache_key}")
        db_start = time.perf_counter()
        
        # Build filters once
        location_filter = {
            "status": {"$in": ["active", "inactive"] if include_inactive else ["active"]}
        }
        if category:
            location_filter["category"] = category
        if is_published is not None:
            location_filter["is_published"] = is_published

        floor_filter = {
            "building_id": building_id,
            "status": "active"
        }
        if floor_id:
            floor_filter["floor_id"] = floor_id

        try:
            # PARALLEL EXECUTION: All DB queries at once for maximum speed
            building_task = Building.find_one({
                "building_id": building_id,
                "status": "active"
            })
            
            floors_task = Floor.find(floor_filter).sort("floor_number").to_list()
            
            # Execute building and floors queries in parallel
            building, floors = await asyncio.gather(
                building_task, floors_task, return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(building, Exception):
                raise building
            if isinstance(floors, Exception):
                raise floors
                
        except Exception as e:
            logger.error(f"DB query error: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        # Fast 404 handling
        if not building:
            not_found_result = {
                "status": "error", 
                "message": f"Building with ID '{building_id}' not found",
                "data": None
            }
            asyncio.create_task(
                set_cache_background(cache_key, not_found_result, expire=CACHE_TTL["not_found"])
            )
            raise HTTPException(status_code=404, detail=f"Building with ID '{building_id}' not found")

        if not floors:
            empty_result = {
                "status": "success",
                "message": "No floors found for this building",
                "data": LocationsResponse(
                    building_id=building_id,
                    building_name=building.name,
                    floors=[],
                    total_floors=0,
                    total_locations=0
                ).dict()
            }
            asyncio.create_task(
                set_cache_background(cache_key, empty_result, expire=CACHE_TTL["hot_path"])
            )
            return empty_result

        # STEP 4: Parallel location fetching for each floor
        floor_location_tasks = []
        for floor in floors:
            floor_location_filter = {**location_filter, "floor_id": floor.floor_id}
            task = Location.find(floor_location_filter).to_list()
            floor_location_tasks.append((floor, task))

        # Execute all location queries in parallel
        location_results = await asyncio.gather(
            *[task for floor, task in floor_location_tasks], 
            return_exceptions=True
        )

        db_time = time.perf_counter() - db_start

        # STEP 5: ULTRA-FAST response building (< 3ms)
        response_build_start = time.perf_counter()
        
        floors_with_locations = []
        total_locations = 0
        
        # Pre-allocate and cache methods for speed
        floors_append = floors_with_locations.append
        
        # Process results with minimal overhead
        for idx, ((floor, _), locations) in enumerate(zip(floor_location_tasks, location_results)):
            # Handle exceptions from parallel location fetching
            if isinstance(locations, Exception):
                logger.warning(f"Error fetching locations for floor {floor.floor_id}: {locations}")
                locations = []  # Continue with empty locations
            
            # Build location items with minimal object creation
            location_items = []
            location_items_append = location_items.append
            
            for location in locations:
                try:
                    # Direct attribute access for speed - avoid getattr when possible
                    category_val = location.category.value if hasattr(location.category, 'value') else str(location.category)
                    shape_val = location.shape.value if hasattr(location.shape, 'value') else str(location.shape)
                    
                    location_item = LocationItem(
                        location_id=location.location_id,
                        name=location.name,
                        category=category_val,
                        floor_id=location.floor_id,
                        shape=shape_val,
                        x=location.x,
                        y=location.y,
                        width=getattr(location, 'width', None),
                        height=getattr(location, 'height', None),
                        radius=getattr(location, 'radius', None),
                        logo_url=getattr(location, 'logo_url', None),
                        color=location.color,
                        text_color=location.text_color,
                        is_published=location.is_published,
                        description=getattr(location, 'description', None),
                        created_by=getattr(location, 'created_by', None),
                        datetime=location.datetime,
                        status=location.status
                    )
                    location_items_append(location_item)
                except Exception as e:
                    logger.warning(f"Skipping location {getattr(location, 'location_id', 'unknown')}: {e}")
                    continue

            # Create floor with locations
            floor_with_locations = FloorWithLocations(
                floor_id=floor.floor_id,
                floor_name=floor.name,
                floor_number=getattr(floor, 'floor_number', 0),
                floor_plan_url=getattr(floor, 'floor_plan_url', None),
                locations=location_items,
                total_locations=len(location_items)
            )
            
            floors_append(floor_with_locations)
            total_locations += len(location_items)

        # Build final response
        response_data = LocationsResponse(
            building_id=building_id,
            building_name=building.name,
            floors=floors_with_locations,
            total_floors=len(floors_with_locations),
            total_locations=total_locations
        )
        
        final_result = {
            "status": "success",
            "message": f"Retrieved locations for building '{building.name}'",
            "data": response_data.dict()
        }
        
        response_build_time = time.perf_counter() - response_build_start
        
        # STEP 6: Background caching (non-blocking)
        asyncio.create_task(
            set_cache_background(cache_key, final_result, expire=CACHE_TTL["hot_path"])
        )
        
        # Performance logging
        total_time = time.perf_counter() - start_time
        logger.info(f"LOCATIONS PERFORMANCE: DB={db_time*1000:.1f}ms, Response={response_build_time*1000:.1f}ms, Total={total_time*1000:.1f}ms [MISS] - {total_locations} locations")
        
        return final_result

    except HTTPException:
        raise
    except Exception as e:
        total_time = time.perf_counter() - start_time
        logger.exception(f"Locations error after {total_time*1000:.1f}ms: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve locations: {str(e)}"
        )