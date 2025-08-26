
from fastapi import HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from src.datamodel.database.domain.DigitalSignage import Path, Location, FloorSegment
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Path"],
        "summary": "List Paths",
        "response_model": dict,
        "description": "Get all paths with optional filters for building_id, created_by, and is_multi_floor.",
        "response_description": "List of paths",
        "deprecated": False,
    }
    return ApiConfig(**config)


class PathListItem(BaseModel):
    path_id: str
    name: Optional[str] = None
    building_id: str
    created_by: Optional[str] = None

    start_point_id: str
    end_point_id: str
    start_point_name: Optional[str] = None
    end_point_name: Optional[str] = None

    is_published: bool
    is_multifloor: bool
    floors: List[str] = []
    connector_shared_ids: List[str] = []
    floor_segments: List[FloorSegment] = []

    tags: List[str] = []
    datetime: float
    status: str


async def main(
    building_id: Optional[str] = Query(None, description="Filter by building ID"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    is_multi_floor: Optional[bool] = Query(None, description="True for multi-floor paths, False for single-floor"),
):
    try:
        filter_query = {"status": "active"}

        if building_id:
            filter_query["building_id"] = building_id
        if created_by:
            filter_query["created_by"] = created_by
        if is_multi_floor is not None:
            # Path schema uses `is_multifloor`
            filter_query["is_multifloor"] = is_multi_floor

        paths = await Path.find(filter_query).to_list()

        # Prefetch start/end location names
        location_ids = {p.start_point_id for p in paths if getattr(p, "start_point_id", None)} | {p.end_point_id for p in paths if getattr(p, "end_point_id", None)}
        location_names = {}
        if location_ids:
            locations = await Location.find({"location_id": {"$in": list(location_ids)}, "status": "active"}).to_list()
            location_names = {loc.location_id: loc.name for loc in locations}

        path_list: List[PathListItem] = []
        for p in paths:
            item = PathListItem(
                path_id=p.path_id,
                name=p.name,
                building_id=p.building_id,
                created_by=p.created_by,
                start_point_id=p.start_point_id,
                end_point_id=p.end_point_id,
                start_point_name=location_names.get(p.start_point_id),
                end_point_name=location_names.get(p.end_point_id),
                is_published=p.is_published,
                is_multifloor=p.is_multifloor,
                floors=p.floors or [],
                connector_shared_ids=p.connector_shared_ids or [],
                floor_segments=p.floor_segments or [],
                tags=p.tags or [],
                datetime=p.datetime,
                status=p.status,
            )
            path_list.append(item)

        return {
            "status": "success",
            "message": f"Retrieved {len(path_list)} paths",
            "data": {
                "paths": path_list,
                "count": len(path_list),
                "filters_applied": {
                    "building_id": building_id,
                    "created_by": created_by,
                    "is_multi_floor": is_multi_floor,
                },
            },
        }

    except Exception as e:
        logger.exception(f"Error retrieving paths: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve paths: {str(e)}",
        )


# from fastapi import HTTPException, Query, status
# from typing import Optional, List
# from pydantic import BaseModel, Field
# import logging
# import hashlib
# import json

# from src.datamodel.database.domain.DigitalSignage import Path, Location, FloorSegment
# from src.datamodel.datavalidation.apiconfig import ApiConfig
# from src.common.redis_utils import get_cache, set_cache  # <-- Import your Redis utils

# logger = logging.getLogger(__name__)


# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Path"],
#         "summary": "List Paths",
#         "response_model": dict,
#         "description": "Get all paths with optional filters for building_id, created_by, and is_multi_floor.",
#         "response_description": "List of paths",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)


# class PathListItem(BaseModel):
#     path_id: str
#     name: Optional[str] = None
#     building_id: str
#     created_by: Optional[str] = None

#     start_point_id: str
#     end_point_id: str
#     start_point_name: Optional[str] = None
#     end_point_name: Optional[str] = None

#     is_published: bool
#     is_multifloor: bool
#     floors: List[str] = []
#     connector_shared_ids: List[str] = []
#     floor_segments: List[FloorSegment] = []

#     tags: List[str] = []
#     datetime: float
#     status: str


# async def main(
#     building_id: Optional[str] = Query(None, description="Filter by building ID"),
#     created_by: Optional[str] = Query(None, description="Filter by creator"),
#     is_multi_floor: Optional[bool] = Query(None, description="True for multi-floor paths, False for single-floor"),
# ):
#     try:
#         # Build a unique cache key (based on filters)
#         key_raw = json.dumps({
#             "building_id": building_id,
#             "created_by": created_by,
#             "is_multi_floor": is_multi_floor
#         }, sort_keys=True)
#         cache_key = "paths:" + hashlib.md5(key_raw.encode()).hexdigest()

#         # 1️⃣ Try Redis cache first
#         cached_data = await get_cache(cache_key)
#         if cached_data:
#             logger.info(f"Cache hit for key: {cache_key}")
#             return cached_data
#         logger.info(f"Cache miss for key: {cache_key}")

#         # 2️⃣ Fetch from DB
#         filter_query = {"status": "active"}
#         if building_id:
#             filter_query["building_id"] = building_id
#         if created_by:
#             filter_query["created_by"] = created_by
#         if is_multi_floor is not None:
#             filter_query["is_multifloor"] = is_multi_floor

#         paths = await Path.find(filter_query).to_list()

#         # Prefetch start/end location names
#         location_ids = {
#             p.start_point_id for p in paths if getattr(p, "start_point_id", None)
#         } | {
#             p.end_point_id for p in paths if getattr(p, "end_point_id", None)
#         }

#         location_names = {}
#         if location_ids:
#             locations = await Location.find(
#                 {"location_id": {"$in": list(location_ids)}, "status": "active"}
#             ).to_list()
#             location_names = {loc.location_id: loc.name for loc in locations}

#         path_list: List[PathListItem] = []
#         for p in paths:
#             item = PathListItem(
#                 path_id=p.path_id,
#                 name=p.name,
#                 building_id=p.building_id,
#                 created_by=p.created_by,
#                 start_point_id=p.start_point_id,
#                 end_point_id=p.end_point_id,
#                 start_point_name=location_names.get(p.start_point_id),
#                 end_point_name=location_names.get(p.end_point_id),
#                 is_published=p.is_published,
#                 is_multifloor=p.is_multifloor,
#                 floors=p.floors or [],
#                 connector_shared_ids=p.connector_shared_ids or [],
#                 floor_segments=p.floor_segments or [],
#                 tags=p.tags or [],
#                 datetime=p.datetime,
#                 status=p.status,
#             )
#             path_list.append(item)

#         response_data = {
#             "status": "success",
#             "message": f"Retrieved {len(path_list)} paths",
#             "data": {
#                 "paths": [p.dict() for p in path_list],  # Ensure serializable
#                 "count": len(path_list),
#                 "filters_applied": {
#                     "building_id": building_id,
#                     "created_by": created_by,
#                     "is_multi_floor": is_multi_floor,
#                 },
#             },
#         }

#         # 3️⃣ Store in cache (10 mins = 600 sec)
#         await set_cache(cache_key, response_data, expire=600)

#         return response_data

#     except Exception as e:
#         logger.exception(f"Error retrieving paths: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve paths: {str(e)}",
#         )

