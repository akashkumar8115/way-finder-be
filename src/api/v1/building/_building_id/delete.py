# from fastapi import HTTPException, Path, Query, status
# from pydantic import BaseModel
# from typing import Optional
# import time
# import logging
# from src.datamodel.database.domain.DigitalSignage import Building, Floor, Location
# from src.datamodel.datavalidation.apiconfig import ApiConfig


# logger = logging.getLogger(__name__)


# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Building"],
#         "summary": "Delete Building",
#         "response_model": dict,
#         "description": "Delete a building by ID. Can perform soft delete (default) or hard delete.",
#         "response_description": "Deletion confirmation",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)


# class DeleteResponse(BaseModel):
#     deleted_id: str
#     delete_type: str
#     affected_floors: int
#     affected_locations: int
#     message: str


# async def main(
#     building_id: str = Path(..., description="Building ID to delete"),
#     hard_delete: Optional[bool] = Query(False, description="Perform hard delete (true) or soft delete (false)"),
#     cascade: Optional[bool] = Query(True, description="Also delete associated floors and locations")
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

#         affected_floors = 0
#         affected_locations = 0

#         # Handle cascade deletion of floors and locations
#         if cascade and building.floors:
#             # Get all floors in this building
#             floors = await Floor.find({
#                 "building_id": building_id,
#                 "status": "active"
#             }).to_list()
            
#             affected_floors = len(floors)
            
#             for floor in floors:
#                 # Handle locations in each floor
#                 if floor.locations:
#                     locations = await Location.find({
#                         "location_id": {"$in": floor.locations},
#                         "status": "active"
#                     }).to_list()
                    
#                     affected_locations += len(locations)
                    
#                     # Delete or soft delete locations
#                     for location in locations:
#                         if hard_delete:
#                             await location.delete()
#                         else:
#                             location.status = "deleted"
#                             location.updated_by = None  # Set to current user if available
#                             location.update_on = time.time()
#                             await location.save()
                
#                 # Delete or soft delete floor
#                 if hard_delete:
#                     await floor.delete()
#                 else:
#                     floor.status = "deleted"
#                     floor.updated_by = None  # Set to current user if available
#                     floor.update_on = time.time()
#                     await floor.save()

#         # Delete or soft delete building
#         if hard_delete:
#             await building.delete()
#             delete_type = "hard"
#         else:
#             building.status = "deleted"
#             building.updated_by = None  # Set to current user if available
#             building.update_on = time.time()
#             await building.save()
#             delete_type = "soft"

#         logger.info(f"Building {delete_type} deleted: {building_id}, affected floors: {affected_floors}, affected locations: {affected_locations}")

#         response = DeleteResponse(
#             deleted_id=building_id,
#             delete_type=delete_type,
#             affected_floors=affected_floors,
#             affected_locations=affected_locations,
#             message=f"Building {delete_type} deleted successfully"
#         )

#         return {
#             "status": "success",
#             "message": f"Building {delete_type} deleted successfully",
#             "data": response
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception(f"Error deleting building: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to delete building: {str(e)}"
#         )

# casing file

from fastapi import HTTPException, Path, Query, status
from pydantic import BaseModel
from typing import Optional
import time
import logging
import asyncio
from src.datamodel.database.domain.DigitalSignage import Building, Floor, Location
from src.datamodel.datavalidation.apiconfig import ApiConfig
# Import your Redis cache functions
from src.common.redis_utils import (
    get_cache_fast, 
    set_cache_fast, 
    get_multi_cache_fast,
    set_cache_background,
    delete_multi_cache,
    redis_client
)

logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Building"],
        "summary": "Delete Building",
        "response_model": dict,
        "description": "Delete a building by ID. Can perform soft delete (default) or hard delete.",
        "response_description": "Deletion confirmation",
        "deprecated": False,
    }
    return ApiConfig(**config)


class DeleteResponse(BaseModel):
    deleted_id: str
    delete_type: str
    affected_floors: int
    affected_locations: int
    message: str


async def main(
    building_id: str = Path(..., description="Building ID to delete"),
    hard_delete: Optional[bool] = Query(False, description="Perform hard delete (true) or soft delete (false)"),
    cascade: Optional[bool] = Query(True, description="Also delete associated floors and locations")
):
    try:
        # Define cache keys
        building_cache_key = f"building:{building_id}"
        floors_cache_key = f"building:{building_id}:floors"
        locations_cache_key = f"building:{building_id}:locations"
        
        

        # Try to get building from cache first
        cached_building = await get_cache_fast(building_cache_key)
        
        if cached_building:
            logger.info(f"Building {building_id} found in cache")
            building_data = cached_building
        else:
            # Find building by ID from database
            building = await Building.find_one({
                "building_id": building_id
            })
            
            if not building:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Building with ID '{building_id}' not found"
                )
            
            building_data = building.dict() if hasattr(building, 'dict') else building
            # Cache the building for future requests (cache for 5 minutes)
            await set_cache_background(building_cache_key, building_data, expire=300)

        affected_floors = 0
        affected_locations = 0

        # Handle cascade deletion of floors and locations
        if cascade and building_data.get('floors'):
            # Try to get floors from cache first
            cached_floors = await get_cache_fast(floors_cache_key)
            
            if cached_floors:
                floors_data = cached_floors
                logger.info(f"Floors for building {building_id} found in cache")
            else:
                # Get all floors in this building from database
                floors = await Floor.find({
                    "building_id": building_id,
                    "status": "active"
                }).to_list()
                
                floors_data = [floor.dict() if hasattr(floor, 'dict') else floor for floor in floors]
                # Cache floors data
                await set_cache_background(floors_cache_key, floors_data, expire=300)
            
            affected_floors = len(floors_data)
            
            # Collect all location IDs for batch processing
            all_location_ids = []
            for floor_data in floors_data:
                if floor_data.get('locations'):
                    all_location_ids.extend(floor_data['locations'])
            
            if all_location_ids:
                # Try to get locations from cache
                cached_locations = await get_cache_fast(locations_cache_key)
                
                if cached_locations:
                    locations_data = cached_locations
                    logger.info(f"Locations for building {building_id} found in cache")
                else:
                    # Get locations from database
                    locations = await Location.find({
                        "location_id": {"$in": all_location_ids},
                        "status": "active"
                    }).to_list()
                    
                    locations_data = [loc.dict() if hasattr(loc, 'dict') else loc for loc in locations]
                    # Cache locations data
                    await set_cache_background(locations_cache_key, locations_data, expire=300)
                
                affected_locations = len(locations_data)
                
                # Delete or soft delete locations
                for location_data in locations_data:
                    # Get the actual location object for deletion
                    location = await Location.find_one({"location_id": location_data['location_id']})
                    if location:
                        if hard_delete:
                            await location.delete()
                        else:
                            location.status = "deleted"
                            location.updated_by = None  # Set to current user if available
                            location.update_on = time.time()
                            await location.save()
            
            # Delete or soft delete floors
            for floor_data in floors_data:
                # Get the actual floor object for deletion
                floor = await Floor.find_one({"floor_id": floor_data.get('floor_id')})
                if floor:
                    if hard_delete:
                        await floor.delete()
                    else:
                        floor.status = "deleted"
                        floor.updated_by = None  # Set to current user if available
                        floor.update_on = time.time()
                        await floor.save()

        # Delete or soft delete building
        # Get the actual building object for deletion
        building = await Building.find_one({"building_id": building_id})
        if building:
            if hard_delete:
                await building.delete()
                delete_type = "hard"
            else:
                building.status = "deleted"
                building.updated_by = None  # Set to current user if available
                building.update_on = time.time()
                await building.save()
                delete_type = "soft"
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building with ID '{building_id}' not found for deletion"
            )

        # Clear related cache entries after successful deletion
        cache_keys_to_clear = [
            building_cache_key,
            floors_cache_key, 
            locations_cache_key,
            f"buildings:list",  # Clear building list cache if exists
            f"buildings:active",  # Clear active buildings cache if exists
        ]
        
        # Clear cache in background (fire and forget)
        # for cache_key in cache_keys_to_clear:
        #     asyncio.create_task(redis_client.delete(cache_key))
        asyncio.create_task(delete_multi_cache(cache_keys_to_clear))    
        logger.info(f"Building {delete_type} deleted: {building_id}, affected floors: {affected_floors}, affected locations: {affected_locations}")

        response = DeleteResponse(
            deleted_id=building_id,
            delete_type=delete_type,
            affected_floors=affected_floors,
            affected_locations=affected_locations,
            message=f"Building {delete_type} deleted successfully"
        )

        # Cache the deletion response for audit purposes (short TTL)
        deletion_log_key = f"deletion_log:{building_id}:{int(time.time())}"
        await set_cache_background(deletion_log_key, {
            "building_id": building_id,
            "delete_type": delete_type,
            "timestamp": time.time(),
            "affected_floors": affected_floors,
            "affected_locations": affected_locations
        }, expire=86400)  # Keep for 24 hours

        return {
            "status": "success",
            "message": f"Building {delete_type} deleted successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting building: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete building: {str(e)}"
        )

# 3rd attempt after redis utils refactor
# from fastapi import HTTPException, Path, Query, status, Request, Depends
# from pydantic import BaseModel, Field
# from typing import Optional, List, Dict, Any
# import time
# import logging
# import asyncio
# from sqlalchemy.ext.asyncio import AsyncSession

# from src.datamodel.database.domain.DigitalSignage import Building, Floor, Location
# from src.datamodel.datavalidation.apiconfig import ApiConfig
# from src.core.middleware.token_validate_middleware import validate_token
# from src.core.database.dbs.getdb import postresql as db

# # Import your Redis cache functions
# from src.common.redis_utils import (
#     get_cache_fast, 
#     set_cache_fast, 
#     get_multi_cache_fast,
#     set_multi_cache_fast,
#     set_cache_background,
#     redis_client
# )

# logger = logging.getLogger(__name__)

# # Optimized cache configuration
# CACHE_TTL = {
#     "building": 7200,       # 2 hours for building data
#     "floors": 3600,         # 1 hour for floor data
#     "locations": 1800,      # 30 minutes for location data
#     "deletion_log": 86400,  # 24 hours for deletion audit
#     "negative": 300,        # 5 minutes for negative results
# }

# # Cache key patterns for consistency
# CACHE_KEYS = {
#     "building": "bld:{entity_uuid}:{building_id}",
#     "building_simple": "bld:{building_id}",
#     "floors": "bld_flrs:{building_id}",
#     "locations": "bld_locs:{building_id}",
#     "floor": "flr:{floor_id}",
#     "location": "loc:{location_id}",
#     "deletion_log": "del_log:{building_id}:{timestamp}",
#     "lists": "bld_list:{entity_uuid}*",
# }

# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Building"],
#         "summary": "Delete Building",
#         "response_model": dict,
#         "description": "Delete a building by ID with optimized caching. Supports soft delete (default) or hard delete with cascade options.",
#         "response_description": "Deletion confirmation with performance metrics",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)

# class DeleteResponse(BaseModel):
#     deleted_id: str
#     delete_type: str
#     affected_floors: int
#     affected_locations: int
#     message: str
#     execution_time_ms: float
#     cache_invalidated: int

#     class Config:
#         from_attributes = True

# class DeletionAudit(BaseModel):
#     building_id: str
#     building_name: str
#     entity_uuid: Optional[str] = None
#     delete_type: str
#     deleted_by: Optional[str] = None
#     timestamp: float
#     affected_floors: int
#     affected_locations: int
#     floor_ids: List[str] = []
#     location_ids: List[str] = []

# async def _get_building_with_smart_cache(building_id: str, entity_uuid: str = None) -> Optional[Dict[str, Any]]:
#     """
#     Smart building retrieval with multi-level caching
#     """
#     # Try entity-specific cache first if entity_uuid is provided
#     cache_keys = []
#     if entity_uuid:
#         cache_keys.append(CACHE_KEYS["building"].format(entity_uuid=entity_uuid, building_id=building_id))
#     cache_keys.append(CACHE_KEYS["building_simple"].format(building_id=building_id))
    
#     start_time = time.perf_counter()
    
#     # Try multiple cache keys
#     for cache_key in cache_keys:
#         try:
#             cached_building = await get_cache_fast(cache_key)
#             if cached_building is not None:
#                 if cached_building.get("not_found"):
#                     return None
                    
#                 cache_time = time.perf_counter() - start_time
#                 logger.info(f"Cache HIT for building delete {building_id} in {cache_time*1000:.2f}ms")
#                 return cached_building
#         except Exception as e:
#             logger.warning(f"Cache retrieval error for key {cache_key}: {e}")
    
#     # Cache miss - fetch from database
#     db_start = time.perf_counter()
#     try:
#         query_filter = {"building_id": building_id, "status": {"$ne": "deleted"}}
#         if entity_uuid:
#             query_filter["entity_uuid"] = entity_uuid
            
#         building = await Building.find_one(query_filter)
        
#         db_time = time.perf_counter() - db_start
#         logger.info(f"Database fetch for building {building_id} took {db_time*1000:.2f}ms")
        
#         if building:
#             building_dict = building.dict()
#             # Cache in multiple locations for faster future access
#             for cache_key in cache_keys:
#                 asyncio.create_task(
#                     set_cache_fast(cache_key, building_dict, expire=CACHE_TTL["building"])
#                 )
#             return building_dict
#         else:
#             # Cache negative result
#             not_found_data = {"not_found": True}
#             for cache_key in cache_keys:
#                 asyncio.create_task(
#                     set_cache_fast(cache_key, not_found_data, expire=CACHE_TTL["negative"])
#                 )
#             return None
            
#     except Exception as e:
#         logger.error(f"Database error fetching building {building_id}: {e}")
#         return None

# async def _get_floors_with_batch_cache(building_id: str, floor_ids: List[str]) -> List[Dict[str, Any]]:
#     """
#     Optimized floor retrieval with batch caching
#     """
#     if not floor_ids:
#         return []
        
#     start_time = time.perf_counter()
    
#     # Try building-specific floor cache first
#     building_floors_key = CACHE_KEYS["floors"].format(building_id=building_id)
#     try:
#         cached_floors = await get_cache_fast(building_floors_key)
#         if cached_floors is not None:
#             cache_time = time.perf_counter() - start_time
#             logger.info(f"Building floors cache HIT in {cache_time*1000:.2f}ms")
#             return [floor for floor in cached_floors if floor.get("status") == "active"]
#     except Exception as e:
#         logger.warning(f"Building floors cache error: {e}")
    
#     # Try individual floor caches
#     floors_data = {}
#     uncached_floor_ids = set(floor_ids)
    
#     # Multi-get individual floor caches
#     try:
#         floor_cache_keys = [CACHE_KEYS["floor"].format(floor_id=fid) for fid in floor_ids]
#         cached_individual_floors = await get_multi_cache_fast(floor_cache_keys)
        
#         for cache_key, cached_floor in cached_individual_floors.items():
#             if cached_floor and not cached_floor.get("not_found"):
#                 floor_id = cache_key.split(":", 1)[1]
#                 floors_data[floor_id] = cached_floor
#                 uncached_floor_ids.discard(floor_id)
                
#     except Exception as e:
#         logger.warning(f"Individual floors cache error: {e}")
    
#     # Fetch uncached floors from database
#     if uncached_floor_ids:
#         db_start = time.perf_counter()
#         try:
#             db_floors = await Floor.find({
#                 "floor_id": {"$in": list(uncached_floor_ids)},
#                 "building_id": building_id,
#                 "status": "active"
#             }).to_list()
            
#             db_time = time.perf_counter() - db_start
#             logger.info(f"Database floor fetch took {db_time*1000:.2f}ms for {len(uncached_floor_ids)} floors")
            
#             # Process and cache results
#             new_cache_data = {}
#             for floor in db_floors:
#                 floor_dict = floor.dict()
#                 floors_data[floor.floor_id] = floor_dict
#                 new_cache_data[CACHE_KEYS["floor"].format(floor_id=floor.floor_id)] = floor_dict
            
#             # Batch cache new floor data
#             if new_cache_data:
#                 asyncio.create_task(
#                     set_multi_cache_fast(new_cache_data, expire=CACHE_TTL["floors"])
#                 )
                
#         except Exception as e:
#             logger.error(f"Database error fetching floors: {e}")
    
#     # Convert to list and cache building floors
#     result_floors = [floors_data[fid] for fid in floor_ids if fid in floors_data]
    
#     # Cache the building floors list
#     asyncio.create_task(
#         set_cache_fast(building_floors_key, result_floors, expire=CACHE_TTL["floors"])
#     )
    
#     total_time = time.perf_counter() - start_time
#     logger.info(f"Floor processing completed in {total_time*1000:.2f}ms, returned {len(result_floors)} floors")
    
#     return result_floors

# async def _get_locations_with_batch_cache(building_id: str, location_ids: List[str]) -> List[Dict[str, Any]]:
#     """
#     Optimized location retrieval with batch caching
#     """
#     if not location_ids:
#         return []
        
#     start_time = time.perf_counter()
    
#     # Try building-specific location cache first
#     building_locations_key = CACHE_KEYS["locations"].format(building_id=building_id)
#     try:
#         cached_locations = await get_cache_fast(building_locations_key)
#         if cached_locations is not None:
#             cache_time = time.perf_counter() - start_time
#             logger.info(f"Building locations cache HIT in {cache_time*1000:.2f}ms")
#             return [loc for loc in cached_locations if loc.get("status") == "active"]
#     except Exception as e:
#         logger.warning(f"Building locations cache error: {e}")
    
#     # Multi-get individual location caches
#     locations_data = {}
#     uncached_location_ids = set(location_ids)
    
#     try:
#         location_cache_keys = [CACHE_KEYS["location"].format(location_id=lid) for lid in location_ids]
#         cached_individual_locations = await get_multi_cache_fast(location_cache_keys)
        
#         for cache_key, cached_location in cached_individual_locations.items():
#             if cached_location and not cached_location.get("not_found"):
#                 location_id = cache_key.split(":", 1)[1]
#                 locations_data[location_id] = cached_location
#                 uncached_location_ids.discard(location_id)
                
#     except Exception as e:
#         logger.warning(f"Individual locations cache error: {e}")
    
#     # Fetch uncached locations from database
#     if uncached_location_ids:
#         db_start = time.perf_counter()
#         try:
#             db_locations = await Location.find({
#                 "location_id": {"$in": list(uncached_location_ids)},
#                 "status": "active"
#             }).to_list()
            
#             db_time = time.perf_counter() - db_start
#             logger.info(f"Database location fetch took {db_time*1000:.2f}ms for {len(uncached_location_ids)} locations")
            
#             # Process and cache results
#             new_cache_data = {}
#             for location in db_locations:
#                 location_dict = location.dict()
#                 locations_data[location.location_id] = location_dict
#                 new_cache_data[CACHE_KEYS["location"].format(location_id=location.location_id)] = location_dict
            
#             # Batch cache new location data
#             if new_cache_data:
#                 asyncio.create_task(
#                     set_multi_cache_fast(new_cache_data, expire=CACHE_TTL["locations"])
#                 )
                
#         except Exception as e:
#             logger.error(f"Database error fetching locations: {e}")
    
#     # Convert to list and cache building locations
#     result_locations = [locations_data[lid] for lid in location_ids if lid in locations_data]
    
#     # Cache the building locations list
#     asyncio.create_task(
#         set_cache_fast(building_locations_key, result_locations, expire=CACHE_TTL["locations"])
#     )
    
#     total_time = time.perf_counter() - start_time
#     logger.info(f"Location processing completed in {total_time*1000:.2f}ms, returned {len(result_locations)} locations")
    
#     return result_locations

# async def _perform_cascade_deletion(floors_data: List[Dict], locations_data: List[Dict], hard_delete: bool, user_uuid: str = None) -> tuple:
#     """
#     Perform cascaded deletion of floors and locations with batch operations
#     """
#     current_time = time.time()
#     deleted_floors = 0
#     deleted_locations = 0
    
#     # Process locations first (more granular)
#     if locations_data:
#         location_operations = []
#         for location_data in locations_data:
#             try:
#                 location = await Location.find_one({"location_id": location_data['location_id']})
#                 if location:
#                     if hard_delete:
#                         location_operations.append(location.delete())
#                     else:
#                         location.status = "deleted"
#                         location.updated_by = user_uuid
#                         location.update_on = current_time
#                         location_operations.append(location.save())
#             except Exception as e:
#                 logger.error(f"Error preparing location deletion {location_data.get('location_id')}: {e}")
        
#         # Execute location operations in batches
#         if location_operations:
#             try:
#                 await asyncio.gather(*location_operations, return_exceptions=True)
#                 deleted_locations = len(location_operations)
#                 logger.info(f"Processed {deleted_locations} location deletions")
#             except Exception as e:
#                 logger.error(f"Batch location deletion error: {e}")
    
#     # Process floors
#     if floors_data:
#         floor_operations = []
#         for floor_data in floors_data:
#             try:
#                 floor = await Floor.find_one({"floor_id": floor_data['floor_id']})
#                 if floor:
#                     if hard_delete:
#                         floor_operations.append(floor.delete())
#                     else:
#                         floor.status = "deleted"
#                         floor.updated_by = user_uuid
#                         floor.update_on = current_time
#                         floor_operations.append(floor.save())
#             except Exception as e:
#                 logger.error(f"Error preparing floor deletion {floor_data.get('floor_id')}: {e}")
        
#         # Execute floor operations in batches
#         if floor_operations:
#             try:
#                 await asyncio.gather(*floor_operations, return_exceptions=True)
#                 deleted_floors = len(floor_operations)
#                 logger.info(f"Processed {deleted_floors} floor deletions")
#             except Exception as e:
#                 logger.error(f"Batch floor deletion error: {e}")
    
#     return deleted_floors, deleted_locations

# async def _comprehensive_cache_invalidation(building_id: str, building_data: Dict, entity_uuid: str = None) -> int:
#     """
#     Comprehensive cache invalidation with pattern matching and batch operations
#     """
#     cache_keys_to_delete = []
    
#     # Core building caches
#     if entity_uuid:
#         cache_keys_to_delete.append(CACHE_KEYS["building"].format(entity_uuid=entity_uuid, building_id=building_id))
#     cache_keys_to_delete.extend([
#         CACHE_KEYS["building_simple"].format(building_id=building_id),
#         f"bld_detail:{building_id}",  # From GET API
#         CACHE_KEYS["floors"].format(building_id=building_id),
#         CACHE_KEYS["locations"].format(building_id=building_id),
#     ])
    
#     # Entity-specific caches
#     if entity_uuid:
#         cache_keys_to_delete.extend([
#             f"bld_list:{entity_uuid}",
#             f"bld_list:{entity_uuid}:*",
#             f"entity:{entity_uuid}:buildings",
#             f"buildings:active:{entity_uuid}",
#             f"buildings:inactive:{entity_uuid}",
#         ])
    
#     # Floor and location specific caches
#     if building_data.get('floors'):
#         for floor_id in building_data['floors']:
#             cache_keys_to_delete.append(CACHE_KEYS["floor"].format(floor_id=floor_id))
    
#     # Name-based caches
#     if building_data.get('name') and entity_uuid:
#         cache_keys_to_delete.append(f"bld_name:{entity_uuid}:{building_data['name'].lower()}")
    
#     # Execute cache invalidation in batches
#     invalidated_count = 0
#     try:
#         # Direct key deletion
#         if cache_keys_to_delete:
#             # Remove duplicates
#             unique_keys = list(set(cache_keys_to_delete))
#             await redis_client.delete(*unique_keys)
#             invalidated_count += len(unique_keys)
#             logger.info(f"Deleted {len(unique_keys)} specific cache keys")
        
#         # Pattern-based deletion for complex keys
#         patterns_to_delete = []
#         if entity_uuid:
#             patterns_to_delete.extend([
#                 f"bld_list:{entity_uuid}:*",
#                 f"bld_upd:{building_id}:*",
#             ])
        
#         for pattern in patterns_to_delete:
#             try:
#                 keys = await redis_client.keys(pattern)
#                 if keys:
#                     await redis_client.delete(*keys)
#                     invalidated_count += len(keys)
#                     logger.debug(f"Deleted {len(keys)} keys matching pattern {pattern}")
#             except Exception as e:
#                 logger.warning(f"Pattern deletion error for {pattern}: {e}")
        
#     except Exception as e:
#         logger.error(f"Cache invalidation error: {e}")
    
#     logger.info(f"Total cache invalidation: {invalidated_count} keys for building {building_id}")
#     return invalidated_count

# async def _create_deletion_audit(building_data: Dict, delete_type: str, user_uuid: str, affected_floors: int, 
#                                affected_locations: int, floor_ids: List[str], location_ids: List[str]) -> Dict:
#     """
#     Create comprehensive deletion audit log
#     """
#     current_time = time.time()
    
#     audit_data = DeletionAudit(
#         building_id=building_data["building_id"],
#         building_name=building_data.get("name", "Unknown"),
#         entity_uuid=building_data.get("entity_uuid"),
#         delete_type=delete_type,
#         deleted_by=user_uuid,
#         timestamp=current_time,
#         affected_floors=affected_floors,
#         affected_locations=affected_locations,
#         floor_ids=floor_ids,
#         location_ids=location_ids
#     )
    
#     # Cache the audit log
#     audit_key = CACHE_KEYS["deletion_log"].format(building_id=building_data["building_id"], timestamp=int(current_time))
#     asyncio.create_task(
#         set_cache_fast(audit_key, audit_data.dict(), expire=CACHE_TTL["deletion_log"])
#     )
    
#     return audit_data.dict()

# async def main(
#     request: Request,
#     building_id: str = Path(..., description="Building ID to delete"),
#     hard_delete: Optional[bool] = Query(False, description="Perform hard delete (true) or soft delete (false)"),
#     cascade: Optional[bool] = Query(True, description="Also delete associated floors and locations"),
#     db: AsyncSession = Depends(db)
# ):
#     """
#     Optimized building deletion with comprehensive caching and performance monitoring
#     """
#     request_start = time.perf_counter()
    
#     # Validate token and get user info
#     try:
#         validate_token(request)
#         entity_uuid = getattr(request.state, 'entity_uuid', None)
#         user_uuid = getattr(request.state, 'user_uuid', None)
#     except Exception as e:
#         logger.error(f"Token validation failed: {e}")
#         # Continue without user context for backward compatibility
#         entity_uuid = None
#         user_uuid = None

#     try:
#         # Get building with smart caching
#         building_fetch_start = time.perf_counter()
#         building_data = await _get_building_with_smart_cache(building_id, entity_uuid)
#         building_fetch_time = time.perf_counter() - building_fetch_start
        
#         if not building_data:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Building with ID '{building_id}' not found"
#             )
        
#         logger.info(f"PERF: Building fetch took {building_fetch_time*1000:.2f}ms")

#         affected_floors = 0
#         affected_locations = 0
#         floor_ids = []
#         location_ids = []

#         # Handle cascade deletion with optimized data fetching
#         if cascade and building_data.get('floors'):
#             floors_fetch_start = time.perf_counter()
#             floors_data = await _get_floors_with_batch_cache(building_id, building_data['floors'])
#             floors_fetch_time = time.perf_counter() - floors_fetch_start
            
#             affected_floors = len(floors_data)
#             floor_ids = [f.get('floor_id') for f in floors_data]
            
#             logger.info(f"PERF: Floors fetch took {floors_fetch_time*1000:.2f}ms")
            
#             # Collect all location IDs from floors
#             all_location_ids = []
#             for floor_data in floors_data:
#                 if floor_data.get('locations'):
#                     all_location_ids.extend(floor_data['locations'])
            
#             if all_location_ids:
#                 locations_fetch_start = time.perf_counter()
#                 locations_data = await _get_locations_with_batch_cache(building_id, all_location_ids)
#                 locations_fetch_time = time.perf_counter() - locations_fetch_start
                
#                 affected_locations = len(locations_data)
#                 location_ids = [l.get('location_id') for l in locations_data]
                
#                 logger.info(f"PERF: Locations fetch took {locations_fetch_time*1000:.2f}ms")
                
#                 # Perform cascade deletion
#                 cascade_start = time.perf_counter()
#                 deleted_floors, deleted_locations = await _perform_cascade_deletion(
#                     floors_data, locations_data, hard_delete, user_uuid
#                 )
#                 cascade_time = time.perf_counter() - cascade_start
                
#                 logger.info(f"PERF: Cascade deletion took {cascade_time*1000:.2f}ms")
                
#                 # Update counts with actual deletions
#                 affected_floors = deleted_floors
#                 affected_locations = deleted_locations

#         # Delete the building itself
#         building_delete_start = time.perf_counter()
#         try:
#             building = await Building.find_one({"building_id": building_id})
#             if not building:
#                 raise HTTPException(
#                     status_code=status.HTTP_404_NOT_FOUND,
#                     detail=f"Building with ID '{building_id}' not found for deletion"
#                 )
            
#             if hard_delete:
#                 await building.delete()
#                 delete_type = "hard"
#             else:
#                 building.status = "deleted"
#                 building.updated_by = user_uuid
#                 building.update_on = time.time()
#                 await building.save()
#                 delete_type = "soft"
                
#         except Exception as e:
#             logger.error(f"Building deletion error: {e}")
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail=f"Failed to delete building: {str(e)}"
#             )
        
#         building_delete_time = time.perf_counter() - building_delete_start
#         logger.info(f"PERF: Building deletion took {building_delete_time*1000:.2f}ms")

#         # Comprehensive cache invalidation
#         cache_invalidation_start = time.perf_counter()
#         invalidated_count = await _comprehensive_cache_invalidation(building_id, building_data, entity_uuid)
#         cache_invalidation_time = time.perf_counter() - cache_invalidation_start
        
#         logger.info(f"PERF: Cache invalidation took {cache_invalidation_time*1000:.2f}ms")

#         # Create audit log
#         await _create_deletion_audit(
#             building_data, delete_type, user_uuid, affected_floors, 
#             affected_locations, floor_ids, location_ids
#         )

#         # Calculate total execution time
#         total_time = time.perf_counter() - request_start
        
#         logger.info(f"Building {delete_type} deletion completed: {building_id}, "
#                    f"floors: {affected_floors}, locations: {affected_locations}, "
#                    f"total time: {total_time*1000:.2f}ms")

#         # Build response
#         response = DeleteResponse(
#             deleted_id=building_id,
#             delete_type=delete_type,
#             affected_floors=affected_floors,
#             affected_locations=affected_locations,
#             message=f"Building {delete_type} deleted successfully",
#             execution_time_ms=round(total_time * 1000, 2),
#             cache_invalidated=invalidated_count
#         )

#         return {
#             "status": "success",
#             "message": f"Building {delete_type} deleted successfully",
#             "data": response.dict(),
#             "performance": {
#                 "total_time_ms": round(total_time * 1000, 2),
#                 "breakdown": {
#                     "building_fetch_ms": round(building_fetch_time * 1000, 2),
#                     "building_delete_ms": round(building_delete_time * 1000, 2),
#                     "cache_invalidation_ms": round(cache_invalidation_time * 1000, 2)
#                 }
#             }
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         total_time = time.perf_counter() - request_start
#         logger.exception(f"Unexpected error deleting building {building_id} after {total_time*1000:.2f}ms: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to delete building: {str(e)}"
#         )
    
