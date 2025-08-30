from fastapi import HTTPException, Path, Query, status
from pydantic import BaseModel
from typing import Optional
import time
import logging
from src.datamodel.database.domain.DigitalSignage import Building, Floor, Location
from src.datamodel.datavalidation.apiconfig import ApiConfig


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
        # Find building by ID
        building = await Building.find_one({
            "building_id": building_id
        })
        
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building with ID '{building_id}' not found"
            )

        affected_floors = 0
        affected_locations = 0

        # Handle cascade deletion of floors and locations
        if cascade and building.floors:
            # Get all floors in this building
            floors = await Floor.find({
                "building_id": building_id,
                "status": "active"
            }).to_list()
            
            affected_floors = len(floors)
            
            for floor in floors:
                # Handle locations in each floor
                if floor.locations:
                    locations = await Location.find({
                        "location_id": {"$in": floor.locations},
                        "status": "active"
                    }).to_list()
                    
                    affected_locations += len(locations)
                    
                    # Delete or soft delete locations
                    for location in locations:
                        if hard_delete:
                            await location.delete()
                        else:
                            location.status = "deleted"
                            location.updated_by = None  # Set to current user if available
                            location.update_on = time.time()
                            await location.save()
                
                # Delete or soft delete floor
                if hard_delete:
                    await floor.delete()
                else:
                    floor.status = "deleted"
                    floor.updated_by = None  # Set to current user if available
                    floor.update_on = time.time()
                    await floor.save()

        # Delete or soft delete building
        if hard_delete:
            await building.delete()
            delete_type = "hard"
        else:
            building.status = "deleted"
            building.updated_by = None  # Set to current user if available
            building.update_on = time.time()
            await building.save()
            delete_type = "soft"

        logger.info(f"Building {delete_type} deleted: {building_id}, affected floors: {affected_floors}, affected locations: {affected_locations}")

        response = DeleteResponse(
            deleted_id=building_id,
            delete_type=delete_type,
            affected_floors=affected_floors,
            affected_locations=affected_locations,
            message=f"Building {delete_type} deleted successfully"
        )

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

# casing file



# 2nd attepm
# from fastapi import HTTPException, Path, Query, status
# from pydantic import BaseModel
# from typing import Optional
# import time
# import logging
# import asyncio
# from src.datamodel.database.domain.DigitalSignage import Building, Floor, Location
# from src.datamodel.datavalidation.apiconfig import ApiConfig
# from src.common.redis_utils import (
#     get_cache_fast,
#     set_cache_background,
#     delete_multi_cache,
#     redis_client,
# )
# from src.api.v1.building.get import (
#     _MEMORY_CACHE,
#     _CACHE_ACCESS_ORDER,
# )

# logger = logging.getLogger(__name__)

# CACHE_KEYS = {
#     "building": "bld:{entity_uuid}:{building_id}",
#     "detail": "bld_detail:{building_id}",
#     "floors": "bld:{building_id}:floors",
#     "locations": "bld:{building_id}:locations",
#     "list": "bld_list:{entity_uuid}",
#     "active_list": "buildings:active:{entity_uuid}",
#     "inactive_list": "buildings:inactive:{entity_uuid}",
# }

# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Building"],
#         "summary": "Delete Building",
#         "response_model": dict,
#         "description": "Delete a building by ID. Can perform soft delete (default) or hard delete. Cascades floors & locations.",
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

# def invalidate_memory_cache_by_building(building_id: str):
#     keys_to_del = [k for k in _MEMORY_CACHE if building_id in k]
#     for k in keys_to_del:
#         _MEMORY_CACHE.pop(k, None)
#         try: _CACHE_ACCESS_ORDER.remove(k)
#         except ValueError: pass
#     return keys_to_del

# async def invalidate_redis_caches_by_building(entity_uuid: str, building_id: str):
#     # Wildcard/pattern deletion for all related Redis cache keys
#     patterns = [
#         CACHE_KEYS["building"].format(entity_uuid=entity_uuid, building_id=building_id),
#         CACHE_KEYS["detail"].format(building_id=building_id),
#         CACHE_KEYS["floors"].format(building_id=building_id),
#         CACHE_KEYS["locations"].format(building_id=building_id),
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
#     building_id: str = Path(..., description="Building ID to delete"),
#     entity_uuid: Optional[str] = Query(None, description="Entity UUID for cache invalidation"),
#     hard_delete: Optional[bool] = Query(False, description="Perform hard delete (true) or soft delete (false)"),
#     cascade: Optional[bool] = Query(True, description="Also delete associated floors and locations"),
# ):
#     try:
#         # If entity_uuid is not provided, fetch it from building obj
#         building = await Building.find_one({"building_id": building_id})
#         if not building:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Building with ID '{building_id}' not found",
#             )
#         if not entity_uuid:
#             entity_uuid = getattr(building, 'entity_uuid', None)

#         affected_floors = 0
#         affected_locations = 0

#         # Cascade delete floors/locations
#         if cascade:
#             floors = await Floor.find({"building_id": building_id, "status": "active"}).to_list()
#             affected_floors = len(floors)
#             for floor in floors:
#                 locations = await Location.find({"floor_id": floor.floor_id, "status": "active"}).to_list()
#                 affected_locations += len(locations)
#                 for location in locations:
#                     if hard_delete:
#                         await location.delete()
#                     else:
#                         location.status = "deleted"
#                         location.update_on = time.time()
#                         await location.save()
#                 if hard_delete:
#                     await floor.delete()
#                 else:
#                     floor.status = "deleted"
#                     floor.update_on = time.time()
#                     await floor.save()

#         # Building itself
#         if hard_delete:
#             await building.delete()
#             delete_type = "hard"
#         else:
#             building.status = "deleted"
#             building.update_on = time.time()
#             await building.save()
#             delete_type = "soft"

#         # -------- Cache Invalidation (Redis + Memory) -------------
#         mem_keys = invalidate_memory_cache_by_building(building_id)
#         if entity_uuid:
#             asyncio.create_task(invalidate_redis_caches_by_building(entity_uuid, building_id))
#         # Also batch delete legacy keys if necessary
#         additional_keys = [
#             f"bld:{building_id}",
#             f"bld_detail:{building_id}",
#             f"bld:{building_id}:floors",
#             f"bld:{building_id}:locations",
#             "bld:list",
#             "bld:active",
#         ]
#         asyncio.create_task(delete_multi_cache(additional_keys))
#         logger.info(f"Invalidated {len(mem_keys)} memory caches for building deletion.")

#         # -------- Short-Term Deletion Log Cache -------------
#         deletion_log_key = f"del_log:bld:{building_id}:{int(time.time())}"
#         await set_cache_background(
#             deletion_log_key,
#             {
#                 "building_id": building_id,
#                 "delete_type": delete_type,
#                 "timestamp": time.time(),
#                 "affected_floors": affected_floors,
#                 "affected_locations": affected_locations,
#             },
#             expire=86400,
#         )

#         logger.info(
#             f"Building {delete_type} deleted: {building_id}, "
#             f"floors={affected_floors}, locations={affected_locations}"
#         )

#         response = DeleteResponse(
#             deleted_id=building_id,
#             delete_type=delete_type,
#             affected_floors=affected_floors,
#             affected_locations=affected_locations,
#             message=f"Building {delete_type} deleted successfully.",
#         )

#         return {"status": "success", "data": response.dict()}

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception(f"Error deleting building {building_id}: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to delete building: {str(e)}",
#         )
