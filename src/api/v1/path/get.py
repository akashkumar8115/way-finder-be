
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
# from pydantic import BaseModel, Field
# from typing import Optional, List
# import logging
# import hashlib
# import json

# from src.datamodel.database.domain.DigitalSignage import Path, Location, FloorSegment
# from src.datamodel.datavalidation.apiconfig import ApiConfig

# # Import your existing Redis utilities
# from src.common.redis_utils import (
#     get_cache_fast, 
#     set_cache_fast, 
#     get_multi_cache_fast, 
#     set_multi_cache_fast,
#     set_cache_background
# )

# logger = logging.getLogger(__name__)

# # Cache configuration
# CACHE_TTL = {
#     "paths": 3000,      # 50 minutes for path data
#     "locations": 6000,  # 100 minutes for location names
#     "result": 1800,     # 30 minutes for final results
# }

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

# def _generate_cache_key(filter_query: dict, prefix: str = "paths") -> str:
#     """Generate deterministic cache key from filter parameters"""
#     # Sort the filter query to ensure consistent key generation
#     sorted_filters = json.dumps(filter_query, sort_keys=True)
#     query_hash = hashlib.md5(sorted_filters.encode()).hexdigest()[:12]
#     return f"{prefix}:{query_hash}"

# async def _get_location_names_cached(location_ids: set) -> dict:
#     """Get location names with multi-level caching using your Redis utils"""
#     if not location_ids:
#         return {}
    
#     location_names = {}
#     uncached_ids = set(location_ids)
    
#     # Try to get individual location names from cache using your multi-get function
#     location_cache_keys = [f"location_name:{loc_id}" for loc_id in location_ids]
#     cached_locations = await get_multi_cache_fast(location_cache_keys)
    
#     # Extract cached location names
#     for cache_key, cached_name in cached_locations.items():
#         if cached_name:
#             location_id = cache_key.split(":", 2)[1]  # location_name:ID format
#             location_names[location_id] = cached_name
#             uncached_ids.discard(location_id)
    
#     # Fetch uncached locations from database
#     if uncached_ids:
#         logger.info(f"Fetching {len(uncached_ids)} location names from database")
#         try:
#             locations = await Location.find({
#                 "location_id": {"$in": list(uncached_ids)}, 
#                 "status": "active"
#             }).to_list()
            
#             # Build cache data for new locations
#             new_cache_data = {}
#             for loc in locations:
#                 location_names[loc.location_id] = loc.name
#                 new_cache_data[f"location_name:{loc.location_id}"] = loc.name
            
#             # Cache new location names using your multi-set function
#             if new_cache_data:
#                 await set_multi_cache_fast(new_cache_data, expire=CACHE_TTL["locations"])
                
#         except Exception as e:
#             logger.error(f"Error fetching locations from database: {e}")
    
#     return location_names

# async def _get_paths_cached(filter_query: dict) -> List[Path]:
#     """Get paths with caching using your Redis utils"""
#     cache_key = _generate_cache_key(filter_query, "paths_query")
    
#     # Try cache first using your get function
#     cached_paths = await get_cache_fast(cache_key)
#     if cached_paths is not None:
#         logger.info(f"Cache hit for paths query: {cache_key}")
#         try:
#             # Convert cached data back to Path objects
#             return [Path(**path_data) for path_data in cached_paths]
#         except Exception as e:
#             logger.warning(f"Error converting cached data to Path objects: {e}")
#             # Continue to database fetch if conversion fails
    
#     # Cache miss - fetch from database
#     logger.info(f"Cache miss for paths query: {cache_key}")
#     try:
#         paths = await Path.find(filter_query).to_list()
        
#         # Cache the results (convert to dict for serialization)
#         if paths:  # Only cache if we have data
#             path_dicts = []
#             for path in paths:
#                 try:
#                     path_dicts.append(path.dict())
#                 except Exception as e:
#                     # If dict() fails, try manual conversion
#                     logger.warning(f"Error converting path to dict: {e}")
#                     continue
            
#             # Use background caching to avoid blocking
#             await set_cache_background(cache_key, path_dicts, expire=CACHE_TTL["paths"])
        
#         return paths
        
#     except Exception as e:
#         logger.error(f"Error fetching paths from database: {e}")
#         return []

# async def main(
#     building_id: Optional[str] = Query(None, description="Filter by building ID"),
#     created_by: Optional[str] = Query(None, description="Filter by creator"),
#     is_multi_floor: Optional[bool] = Query(None, description="True for multi-floor paths, False for single-floor"),
# ):
#     try:
#         # Build filter query
#         filter_query = {"status": "active"}
#         if building_id:
#             filter_query["building_id"] = building_id
#         if created_by:
#             filter_query["created_by"] = created_by
#         if is_multi_floor is not None:
#             filter_query["is_multifloor"] = is_multi_floor

#         # Generate cache key for final result
#         result_cache_key = _generate_cache_key(filter_query, "paths_result")
        
#         # Check for cached final result first using your get function
#         cached_result = await get_cache_fast(result_cache_key)
#         if cached_result is not None:
#             logger.info(f"Returning cached result for: {result_cache_key}")
#             return cached_result

#         # Get paths (with caching)
#         paths = await _get_paths_cached(filter_query)
        
#         if not paths:
#             # Return empty result but still cache it briefly to avoid repeated DB calls
#             empty_result = {
#                 "status": "success",
#                 "message": "No paths found matching the criteria",
#                 "data": {
#                     "paths": [],
#                     "count": 0,
#                     "filters_applied": {
#                         "building_id": building_id,
#                         "created_by": created_by,
#                         "is_multi_floor": is_multi_floor,
#                     },
#                 },
#             }
#             await set_cache_background(result_cache_key, empty_result, expire=60)  # Cache empty results for 1 minute
#             return empty_result

#         # Extract unique location IDs
#         location_ids = set()
#         for p in paths:
#             if getattr(p, "start_point_id", None):
#                 location_ids.add(p.start_point_id)
#             if getattr(p, "end_point_id", None):
#                 location_ids.add(p.end_point_id)

#         # Get location names (with caching)
#         location_names = await _get_location_names_cached(location_ids)

#         # Build response data
#         path_list: List[PathListItem] = []
#         for p in paths:
#             try:
#                 item = PathListItem(
#                     path_id=p.path_id,
#                     name=getattr(p, 'name', None),
#                     building_id=p.building_id,
#                     created_by=getattr(p, 'created_by', None),
#                     start_point_id=p.start_point_id,
#                     end_point_id=p.end_point_id,
#                     start_point_name=location_names.get(p.start_point_id),
#                     end_point_name=location_names.get(p.end_point_id),
#                     is_published=getattr(p, 'is_published', False),
#                     is_multifloor=getattr(p, 'is_multifloor', False),
#                     floors=getattr(p, 'floors', []) or [],
#                     connector_shared_ids=getattr(p, 'connector_shared_ids', []) or [],
#                     floor_segments=getattr(p, 'floor_segments', []) or [],
#                     tags=getattr(p, 'tags', []) or [],
#                     datetime=p.datetime,
#                     status=p.status,
#                 )
#                 path_list.append(item)
#             except Exception as e:
#                 logger.warning(f"Error creating PathListItem for path {getattr(p, 'path_id', 'unknown')}: {e}")
#                 continue

#         # Build final response
#         result = {
#             "status": "success",
#             "message": f"Retrieved {len(path_list)} paths",
#             "data": {
#                 "paths": [item.dict() for item in path_list],  # Convert to dict for caching
#                 "count": len(path_list),
#                 "filters_applied": {
#                     "building_id": building_id,
#                     "created_by": created_by,
#                     "is_multi_floor": is_multi_floor,
#                 },
#             },
#         }

#         # Cache the final result in background using your background cache function
#         await set_cache_background(result_cache_key, result, expire=CACHE_TTL["result"])

#         logger.info(f"Successfully retrieved {len(path_list)} paths with filters: {filter_query}")
#         return result

#     except Exception as e:
#         logger.exception(f"Error retrieving paths: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve paths: {str(e)}",
#         )
    