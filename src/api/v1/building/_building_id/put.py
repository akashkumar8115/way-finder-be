from fastapi import HTTPException, Depends, status, Request
from pydantic import BaseModel, Field
from typing import Optional
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
        "status_code": 200,
        "tags": ["Building"],
        "summary": "Update Building",
        "response_model": dict,
        "description": "Update an existing building in the way-finder system.",
        "response_description": "Updated building data",
        "deprecated": False,
    }
    return ApiConfig(**config)


class BuildingUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Name of the building")
    address: Optional[str] = Field(None, description="Building address")
    description: Optional[str] = Field(None, description="Description of the building")
    status: Optional[str] = Field(None, description="Building status (active/inactive)")

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


async def main(
    request: Request,
    building_id: str,
    building_data: BuildingUpdateRequest,
    db: AsyncSession = Depends(db)
):
    """Main handler for building updates"""
    # Validate token and get user info
    validate_token_start = time.time()
    validate_token(request)
    entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    try:
        # Find the existing building
        existing_building = await Building.find_one({
            "building_id": building_id,
            "entity_uuid": entity_uuid,
            "status": {"$ne": "deleted"}  # Exclude deleted buildings
        })
        
        if not existing_building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building with ID '{building_id}' not found"
            )

        # Check if name is being updated and if it conflicts with existing buildings
        if building_data.name and building_data.name != existing_building.name:
            name_conflict = await Building.find_one({
                "name": building_data.name,
                "entity_uuid": entity_uuid,
                "building_id": {"$ne": building_id},  # Exclude current building
                "status": "active"
            })
            
            if name_conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Building with name '{building_data.name}' already exists"
                )

        # Update only provided fields
        update_data = {}
        if building_data.name is not None:
            update_data["name"] = building_data.name
        if building_data.address is not None:
            update_data["address"] = building_data.address
        if building_data.description is not None:
            update_data["description"] = building_data.description
        if building_data.status is not None:
            # Validate status values
            if building_data.status not in ["active", "inactive"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Status must be either 'active' or 'inactive'"
                )
            update_data["status"] = building_data.status

        # Add update metadata
        update_data["update_on"] = time.time()
        update_data["updated_by"] = user_uuid

        # Update the building
        await existing_building.update({"$set": update_data})
        
        # Refresh the building data
        updated_building = await Building.find_one({"building_id": building_id})
        
        logger.info(f"Building updated successfully: {building_id}")

        # Prepare response
        response = BuildingResponse(
            building_id=updated_building.building_id,
            name=updated_building.name,
            address=updated_building.address,
            floors=updated_building.floors or [],
            entity_uuid=updated_building.entity_uuid,
            description=updated_building.description,
            datetime=updated_building.datetime,
            update_on=updated_building.update_on,
            updated_by=updated_building.updated_by,
            status=updated_building.status
        )

        return {
            "status": "success",
            "message": "Building updated successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating building: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update building: {str(e)}"
        )



    # 2nd attemps
# from fastapi import HTTPException, Depends, status, Request, Path
# from pydantic import BaseModel, Field, validator
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
#     redis_client,
# )

# # In-memory cache layer (import or copy these from your GET API)
# _MEMORY_CACHE: dict = {}
# _CACHE_ACCESS_ORDER: list = []
# MAX_MEMORY_CACHE = 100

# def add_to_memory_cache(key: str, data: dict):
#     global _MEMORY_CACHE, _CACHE_ACCESS_ORDER
#     if key in _MEMORY_CACHE:
#         try: _CACHE_ACCESS_ORDER.remove(key)
#         except ValueError: pass
#     elif len(_MEMORY_CACHE) >= MAX_MEMORY_CACHE:
#         oldest = _CACHE_ACCESS_ORDER.pop(0)
#         del _MEMORY_CACHE[oldest]
#     _MEMORY_CACHE[key] = data
#     _CACHE_ACCESS_ORDER.append(key)

# def invalidate_memory_cache(keys: list):
#     removed = 0
#     for key in keys:
#         if key in _MEMORY_CACHE:
#             _MEMORY_CACHE.pop(key, None)
#             try: _CACHE_ACCESS_ORDER.remove(key)
#             except ValueError: pass
#             removed += 1
#     return removed

# CACHE_TTL = {
#     "building": 7200,   # 2 hours for building data
#     "result": 1800,     # 30 minutes for API responses
#     "list": 900,        # 15 minutes for building lists
#     "name_check": 600,  # 10 minutes for name conflict checks
#     "negative": 300,    # 5 minutes for negative results
# }

# CACHE_KEYS = {
#     "building": "bld:{entity_uuid}:{building_id}",
#     "name_check": "bld_name:{entity_uuid}:{name}",
#     "list": "bld_list:{entity_uuid}",
#     "result": "bld_upd:{building_id}:{timestamp}",
#     "entity_buildings": "entity:{entity_uuid}:buildings",
#     "detail": "bld_detail:{building_id}",
#     "active_list": "buildings:active:{entity_uuid}",
#     "inactive_list": "buildings:inactive:{entity_uuid}",
# }

# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Building"],
#         "summary": "Update Building",
#         "response_model": dict,
#         "description": "Update an existing building in the way-finder system with optimized caching.",
#         "response_description": "Updated building data",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)

# class BuildingUpdateRequest(BaseModel):
#     name: Optional[str] = Field(None, min_length=1, max_length=255)
#     address: Optional[str] = Field(None, max_length=500)
#     description: Optional[str] = Field(None, max_length=1000)
#     status: Optional[str] = Field(None)

#     @validator('name')
#     def validate_name(cls, v):
#         if v is not None:
#             v = v.strip()
#             if not v:
#                 raise ValueError('Name cannot be empty or whitespace')
#         return v

#     @validator('status')
#     def validate_status(cls, v):
#         if v is not None and v not in ["active", "inactive"]:
#             raise ValueError('Status must be either \"active\" or \"inactive\"')
#         return v

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
#         from_attributes = True

# async def _get_building_with_cache(building_id: str, entity_uuid: str) -> Optional[Building]:
#     cache_key = CACHE_KEYS["building"].format(entity_uuid=entity_uuid, building_id=building_id)
#     # Check memory cache first
#     building = _MEMORY_CACHE.get(cache_key)
#     if building is not None:
#         return Building(**building)
#     start_time = time.perf_counter()
#     try:
#         cached_building = await get_cache_fast(cache_key)
#         if cached_building is not None:
#             if cached_building.get("not_found"):
#                 return None
#             add_to_memory_cache(cache_key, cached_building)
#             return Building(**cached_building)
#     except Exception as e:
#         pass
#     try:
#         building = await Building.find_one({
#             "building_id": building_id,
#             "entity_uuid": entity_uuid,
#             "status": {"$ne": "deleted"}
#         })
#         if building:
#             building_dict = building.dict()
#             asyncio.create_task(set_cache_fast(cache_key, building_dict, expire=CACHE_TTL["building"]))
#             add_to_memory_cache(cache_key, building_dict)
#         else:
#             asyncio.create_task(set_cache_fast(cache_key, {"not_found": True}, expire=CACHE_TTL["negative"]))
#         return building
#     except Exception as e:
#         return None

# async def _check_name_conflict_optimized(name: str, entity_uuid: str, building_id: str) -> bool:
#     cache_key = CACHE_KEYS["name_check"].format(entity_uuid=entity_uuid, name=name.lower())
#     try:
#         cached_conflict = await get_cache_fast(cache_key)
#         if cached_conflict is not None:
#             conflicting_id = cached_conflict.get('building_id')
#             if conflicting_id and conflicting_id != building_id:
#                 return True
#             return False
#     except Exception:
#         pass
#     try:
#         name_conflict = await Building.find_one({
#             "name": {"$regex": f"^{name}$", "$options": "i"},
#             "entity_uuid": entity_uuid,
#             "building_id": {"$ne": building_id},
#             "status": "active"
#         })
#         if name_conflict:
#             conflict_data = {
#                 "building_id": name_conflict.building_id,
#                 "exists": True,
#                 "name": name_conflict.name
#             }
#             asyncio.create_task(set_cache_fast(cache_key, conflict_data, expire=CACHE_TTL["name_check"]))
#             return True
#         else:
#             no_conflict_data = {"building_id": None, "exists": False}
#             asyncio.create_task(set_cache_fast(cache_key, no_conflict_data, expire=CACHE_TTL["name_check"]))
#             return False
#     except Exception:
#         return False

# async def _delete_by_pattern(pattern: str):
#     try:
#         keys = await redis_client.keys(pattern)
#         if keys:
#             await redis_client.delete(*keys)
#             invalidate_memory_cache(keys)
#     except Exception:
#         pass

# async def _invalidate_related_caches_optimized(building_id: str, entity_uuid: str, old_name: str = None, new_name: str = None):
#     # Core keys
#     keys_to_delete = [
#         CACHE_KEYS["building"].format(entity_uuid=entity_uuid, building_id=building_id),
#         CACHE_KEYS["detail"].format(building_id=building_id),
#         CACHE_KEYS["list"].format(entity_uuid=entity_uuid),
#         CACHE_KEYS["entity_buildings"].format(entity_uuid=entity_uuid),
#         CACHE_KEYS["active_list"].format(entity_uuid=entity_uuid),
#         CACHE_KEYS["inactive_list"].format(entity_uuid=entity_uuid),
#     ]
#     if old_name:
#         keys_to_delete.append(CACHE_KEYS["name_check"].format(entity_uuid=entity_uuid, name=old_name.lower()))
#     if new_name:
#         keys_to_delete.append(CACHE_KEYS["name_check"].format(entity_uuid=entity_uuid, name=new_name.lower()))
#     # Delete memory cache keys
#     invalidate_memory_cache(keys_to_delete)
#     # Redis delete
#     asyncio.create_task(redis_client.delete(*keys_to_delete))
#     # Wildcard pattern-based invalidation (async)
#     pattern_keys = [
#         f"bld_upd:{building_id}:*",
#         f"bld_list:{entity_uuid}:*",
#     ]
#     for pattern in pattern_keys:
#         asyncio.create_task(_delete_by_pattern(pattern))

# async def main(
#     request: Request,
#     building_id: str = Path(..., description="Building ID to update"),
#     building_data: BuildingUpdateRequest = None,
#     db: AsyncSession = Depends(db)
# ):
#     total_start = time.perf_counter()
#     # Validate token
#     try:
#         validate_token(request)
#         entity_uuid = request.state.entity_uuid
#         user_uuid = request.state.user_uuid
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid authentication token"
#         )
#     try:
#         existing_building = await _get_building_with_cache(building_id, entity_uuid)
#         if not existing_building:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Building with ID '{building_id}' not found"
#             )
#         old_name = existing_building.name
#         if not building_data or not any([
#             building_data.name is not None,
#             building_data.address is not None,
#             building_data.description is not None,
#             building_data.status is not None
#         ]):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="At least one field must be provided for update"
#             )
#         new_name = None
#         if building_data.name and building_data.name != existing_building.name:
#             has_conflict = await _check_name_conflict_optimized(building_data.name, entity_uuid, building_id)
#             if has_conflict:
#                 raise HTTPException(
#                     status_code=status.HTTP_409_CONFLICT,
#                     detail=f"Building with name '{building_data.name}' already exists"
#                 )
#             new_name = building_data.name
#         update_data = {}
#         if building_data.name is not None:
#             update_data["name"] = building_data.name.strip()
#         if building_data.address is not None:
#             update_data["address"] = building_data.address.strip() if building_data.address else None
#         if building_data.description is not None:
#             update_data["description"] = building_data.description.strip() if building_data.description else None
#         if building_data.status is not None:
#             update_data["status"] = building_data.status
#         current_time = time.time()
#         update_data["update_on"] = current_time
#         update_data["updated_by"] = user_uuid
#         try:
#             await existing_building.update({"$set": update_data})
#             updated_building = await Building.find_one({"building_id": building_id})
#             if not updated_building:
#                 raise HTTPException(
#                     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                     detail="Failed to retrieve updated building data"
#                 )
#         except Exception as e:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail=f"Failed to update building: {str(e)}"
#             )
#         await _invalidate_related_caches_optimized(
#             building_id, entity_uuid,
#             old_name=old_name if new_name else None,
#             new_name=new_name
#         )
#         response = BuildingResponse(
#             building_id=updated_building.building_id,
#             name=updated_building.name,
#             address=getattr(updated_building, 'address', None),
#             floors=getattr(updated_building, 'floors', []) or [],
#             entity_uuid=updated_building.entity_uuid,
#             description=getattr(updated_building, 'description', None),
#             datetime=updated_building.datetime,
#             update_on=getattr(updated_building, 'update_on', None),
#             updated_by=getattr(updated_building, 'updated_by', None),
#             status=updated_building.status
#         )
#         # Prepare result
#         result = {
#             "status": "success",
#             "message": "Building updated successfully",
#             "data": response.dict(),
#             "metadata": {
#                 "updated_fields": list(update_data.keys()),
#                 "timestamp": current_time
#             }
#         }
#         cache_key = CACHE_KEYS["building"].format(entity_uuid=entity_uuid, building_id=building_id)
#         result_key = CACHE_KEYS["result"].format(building_id=building_id, timestamp=int(current_time))
#         # Update cache (Redis and memory)
#         asyncio.create_task(set_cache_fast(cache_key, updated_building.dict(), expire=CACHE_TTL["building"]))
#         asyncio.create_task(set_cache_fast(result_key, result, expire=CACHE_TTL["result"]))
#         add_to_memory_cache(cache_key, updated_building.dict())
#         # Response with parity
#         total_time = time.perf_counter() - total_start
#         return {
#             "status": "success",
#             "message": "Building updated successfully",
#             "data": response.dict(),
#             "metadata": {
#                 "updated_fields": list(update_data.keys()),
#                 "timestamp": current_time
#             },
#             "performance": {
#                 "X-Response-Time": f"{total_time*1000:.1f}ms"
#             }
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to update building: {str(e)}"
#         )
