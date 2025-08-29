# from fastapi import HTTPException, Path, status
# from pydantic import BaseModel, Field
# from typing import Optional, List
# import logging
# from src.datamodel.database.domain.DigitalSignage import Building, Floor
# from src.datamodel.datavalidation.apiconfig import ApiConfig


# logger = logging.getLogger(__name__)


# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Building"],
#         "summary": "Get Building by ID",
#         "response_model": dict,
#         "description": "Retrieve a specific building by its ID with detailed floor information.",
#         "response_description": "Building details with floors",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)


# class FloorDetailResponse(BaseModel):
#     floor_id: str
#     name: str
#     floor_number: int
#     floor_plan_url: Optional[str] = None
#     locations_count: int
#     description: Optional[str] = None
#     datetime: float
#     status: str

#     class Config:
#         allow_population_by_field_name = True


# class BuildingDetailResponse(BaseModel):
#     building_id: str
#     name: str
#     address: Optional[str] = None
#     floors: List[FloorDetailResponse] = []
#     description: Optional[str] = None
#     created_by: Optional[str] = None
#     datetime: float
#     updated_by: Optional[str] = None
#     update_on: Optional[float] = None
#     status: str

#     class Config:
#         allow_population_by_field_name = True


# async def main(
#     building_id: str = Path(..., description="Building ID to retrieve")
# ):
#     try:
#         # Find building by ID
#         building = await Building.find_one({
#             "building_id": building_id
#         })
        
#         if not building:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Building with ID '{building_id}' not found"
#             )

#         # Get detailed floor information
#         floor_details = []
#         if building.floors:
#             floors = await Floor.find({
#                 "floor_id": {"$in": building.floors},
#                 "status": "active"
#             }).to_list()
            
#             # Sort floors by floor_number
#             floors.sort(key=lambda x: x.floor_number)
            
#             for floor in floors:
#                 floor_detail = FloorDetailResponse(
#                     floor_id=floor.floor_id,
#                     name=floor.name,
#                     floor_number=floor.floor_number,
#                     floor_plan_url=floor.floor_plan_url,
#                     locations_count=len(floor.locations) if floor.locations else 0,
#                     description=floor.description,
#                     datetime=floor.datetime,
#                     status=floor.status
#                 )
#                 floor_details.append(floor_detail)

#         # Prepare response
#         response = BuildingDetailResponse(
#             building_id=building.building_id,
#             name=building.name,
#             address=building.address,
#             floors=floor_details,
#             description=building.description,
#             created_by=building.created_by,
#             datetime=building.datetime,
#             updated_by=building.updated_by,
#             update_on=building.update_on,
#             status=building.status
#         )

#         logger.info(f"Retrieved building details: {building_id}")

#         return {
#             "status": "success",
#             "message": "Building retrieved successfully",
#             "data": response
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception(f"Error retrieving building: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve building: {str(e)}"
#         )


from fastapi import HTTPException, Path, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from src.datamodel.database.domain.DigitalSignage import Building, Floor
from src.datamodel.datavalidation.apiconfig import ApiConfig

# Import your existing Redis utilities
from src.common.redis_utils import (
    get_cache_fast, 
    set_cache_fast, 
    get_multi_cache_fast, 
    set_multi_cache_fast,
    set_cache_background
)

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL = {
    "building": 9000,    # 150 minutes for building data (relatively stable)
    "floors": 6000,      # 100 minutes for floor data 
    "result": 3000,      # 50 minutes for final response
}

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Building"],
        "summary": "Get Building by ID",
        "response_model": dict,
        "description": "Retrieve a specific building by its ID with detailed floor information.",
        "response_description": "Building details with floors",
        "deprecated": False,
    }
    return ApiConfig(**config)

class FloorDetailResponse(BaseModel):
    floor_id: str
    name: str
    floor_number: int
    floor_plan_url: Optional[str] = None
    locations_count: int
    description: Optional[str] = None
    datetime: float
    status: str

    class Config:
        allow_population_by_field_name = True

class BuildingDetailResponse(BaseModel):
    building_id: str
    name: str
    address: Optional[str] = None
    floors: List[FloorDetailResponse] = []
    description: Optional[str] = None
    created_by: Optional[str] = None
    datetime: float
    updated_by: Optional[str] = None
    update_on: Optional[float] = None
    status: str

    class Config:
        allow_population_by_field_name = True

async def _get_building_cached(building_id: str) -> Optional[Building]:
    """Get building data with caching"""
    cache_key = f"building:{building_id}"
    
    # Try cache first
    cached_building = await get_cache_fast(cache_key)
    if cached_building is not None:
        logger.info(f"Cache hit for building: {building_id}")
        try:
            return Building(**cached_building)
        except Exception as e:
            logger.warning(f"Error converting cached building data: {e}")
            # Continue to database fetch if conversion fails
    
    # Cache miss - fetch from database
    logger.info(f"Cache miss for building: {building_id}")
    try:
        building = await Building.find_one({"building_id": building_id})
        
        if building:
            # Cache the building data in background
            try:
                building_dict = building.dict()
                await set_cache_background(cache_key, building_dict, expire=CACHE_TTL["building"])
            except Exception as e:
                logger.warning(f"Error caching building data: {e}")
        
        return building
        
    except Exception as e:
        logger.error(f"Error fetching building from database: {e}")
        return None

async def _get_floors_cached(floor_ids: List[str]) -> List[Floor]:
    """Get multiple floors with batch caching"""
    if not floor_ids:
        return []
    
    floors_data = {}
    uncached_floor_ids = set(floor_ids)
    
    # Try to get cached floors using multi-get
    floor_cache_keys = [f"floor:{floor_id}" for floor_id in floor_ids]
    cached_floors = await get_multi_cache_fast(floor_cache_keys)
    
    # Process cached floors
    for cache_key, cached_floor in cached_floors.items():
        if cached_floor:
            floor_id = cache_key.split(":", 1)[1]
            try:
                floors_data[floor_id] = Floor(**cached_floor)
                uncached_floor_ids.discard(floor_id)
            except Exception as e:
                logger.warning(f"Error converting cached floor {floor_id}: {e}")
    
    # Fetch uncached floors from database
    if uncached_floor_ids:
        logger.info(f"Fetching {len(uncached_floor_ids)} floors from database")
        try:
            db_floors = await Floor.find({
                "floor_id": {"$in": list(uncached_floor_ids)},
                "status": "active"
            }).to_list()
            
            # Cache new floors and add to results
            new_cache_data = {}
            for floor in db_floors:
                floors_data[floor.floor_id] = floor
                try:
                    new_cache_data[f"floor:{floor.floor_id}"] = floor.dict()
                except Exception as e:
                    logger.warning(f"Error converting floor to dict: {e}")
            
            # Cache new floors in background
            if new_cache_data:
                await set_multi_cache_fast(new_cache_data, expire=CACHE_TTL["floors"])
                
        except Exception as e:
            logger.error(f"Error fetching floors from database: {e}")
    
    # Return floors in the same order as requested
    result_floors = []
    for floor_id in floor_ids:
        if floor_id in floors_data:
            result_floors.append(floors_data[floor_id])
    
    return result_floors

async def main(
    building_id: str = Path(..., description="Building ID to retrieve")
):
    try:
        # Check for cached final result first
        result_cache_key = f"building_detail:{building_id}"
        cached_result = await get_cache_fast(result_cache_key)
        if cached_result is not None:
            logger.info(f"Returning cached building detail: {building_id}")
            return cached_result

        # Get building data (with caching)
        building = await _get_building_cached(building_id)
        
        if not building:
            # Cache the 404 result briefly to prevent repeated DB queries
            not_found_result = {
                "status": "error",
                "message": f"Building with ID '{building_id}' not found",
                "data": None
            }
            await set_cache_background(result_cache_key, not_found_result, expire=60)  # Cache for 1 minute
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building with ID '{building_id}' not found"
            )

        # Get detailed floor information (with caching)
        floor_details = []
        if building.floors:
            floors = await _get_floors_cached(building.floors)
            
            # Sort floors by floor_number
            floors.sort(key=lambda x: getattr(x, 'floor_number', 0))
            
            for floor in floors:
                try:
                    floor_detail = FloorDetailResponse(
                        floor_id=floor.floor_id,
                        name=floor.name,
                        floor_number=getattr(floor, 'floor_number', 0),
                        floor_plan_url=getattr(floor, 'floor_plan_url', None),
                        locations_count=len(getattr(floor, 'locations', [])) if getattr(floor, 'locations', None) else 0,
                        description=getattr(floor, 'description', None),
                        datetime=floor.datetime,
                        status=floor.status
                    )
                    floor_details.append(floor_detail)
                except Exception as e:
                    logger.warning(f"Error creating FloorDetailResponse for floor {getattr(floor, 'floor_id', 'unknown')}: {e}")
                    continue

        # Prepare response
        try:
            response = BuildingDetailResponse(
                building_id=building.building_id,
                name=building.name,
                address=getattr(building, 'address', None),
                floors=floor_details,
                description=getattr(building, 'description', None),
                created_by=getattr(building, 'created_by', None),
                datetime=building.datetime,
                updated_by=getattr(building, 'updated_by', None),
                update_on=getattr(building, 'update_on', None),
                status=building.status
            )
        except Exception as e:
            logger.error(f"Error creating BuildingDetailResponse: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing building data"
            )

        # Build final result
        result = {
            "status": "success",
            "message": "Building retrieved successfully",
            "data": response.dict()  # Convert to dict for caching
        }

        # Cache the final result in background
        await set_cache_background(result_cache_key, result, expire=CACHE_TTL["result"])

        logger.info(f"Retrieved building details: {building_id} with {len(floor_details)} floors")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving building: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve building: {str(e)}"
        )