# from fastapi import HTTPException, Path as FastAPIPath, status
# from pydantic import BaseModel
# from typing import Optional, List
# import logging

# from src.datamodel.database.domain.DigitalSignage import Path, Location, VerticalConnector, Floor, NodeKind
# from src.datamodel.datavalidation.apiconfig import ApiConfig

# logger = logging.getLogger(__name__)


# def _dump_without_object_id(doc):
#     """Return a plain dict for a Beanie Document without the internal 'id' (PydanticObjectId)."""
#     if not doc:
#         return None
#     try:
#         # Exclude 'id' which is PydanticObjectId
#         return doc.model_dump(exclude={"id"})
#     except Exception:
#         d = doc.model_dump()
#         d.pop("id", None)
#         return d


# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Path"],
#         "summary": "Get Path by ID",
#         "response_model": dict,
#         "description": "Get a specific navigation path by its ID.",
#         "response_description": "Path details",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)


# class PathDetail(BaseModel):
#     path_id: str
#     name: Optional[str] = None
#     building_id: str
#     created_by: Optional[str] = None

#     start_point_id: str
#     end_point_id: str
#     start_point: Optional[dict] = None
#     end_point: Optional[dict] = None

#     is_published: bool
#     is_multifloor: bool
#     floors: List[str] = []
#     connector_shared_ids: List[str] = []
#     floors_details: List[dict] = []
#     vertical_connectors: List[dict] = []

#     floor_segments: List[dict]

#     tags: List[str] = []
#     datetime: float
#     status: str


# async def main(
#     path_id: str = FastAPIPath(..., description="Path ID to retrieve"),
# ):
#     try:
#         path = await Path.find_one({"path_id": path_id, "status": "active"})
#         if not path:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Path with ID '{path_id}' not found",
#             )

#         # Collect detailed entities for response
#         floor_ids = {seg.floor_id for seg in (path.floor_segments or [])}
#         # Start/End location details (based on Location schema)
#         start_location = await Location.find_one({"location_id": path.start_point_id, "status": "active"})
#         end_location = await Location.find_one({"location_id": path.end_point_id, "status": "active"})

#         # Vertical connectors used to shift between floors (transitions only)
#         vertical_connectors = []
#         if path.is_multifloor:
#             segments = sorted((path.floor_segments or []), key=lambda s: getattr(s, "sequence", 0))
#             transition_shared_ids = set()
#             transition_floor_ids = set()
#             transition_connector_ids = set()

#             def is_vc_point(pt):
#                 kind_val = getattr(pt, "kind", None)
#                 return kind_val == NodeKind.VERTICAL_CONNECTOR or str(kind_val) == "vertical_connector"

#             for i in range(len(segments) - 1):
#                 seg_a = segments[i]
#                 seg_b = segments[i + 1]
#                 if seg_a.floor_id == seg_b.floor_id:
#                     continue
#                 # gather VC shared_ids/ref_ids from both segments
#                 a_shared = {p.shared_id for p in (seg_a.points or []) if is_vc_point(p) and getattr(p, "shared_id", None)}
#                 b_shared = {p.shared_id for p in (seg_b.points or []) if is_vc_point(p) and getattr(p, "shared_id", None)}
#                 common_shared = a_shared & b_shared
#                 if common_shared:
#                     transition_shared_ids.update(common_shared)
#                 else:
#                     transition_shared_ids.update(a_shared or b_shared)

#                 a_ref_ids = {p.ref_id for p in (seg_a.points or []) if is_vc_point(p) and getattr(p, "ref_id", None)}
#                 b_ref_ids = {p.ref_id for p in (seg_b.points or []) if is_vc_point(p) and getattr(p, "ref_id", None)}
#                 transition_connector_ids.update(a_ref_ids)
#                 transition_connector_ids.update(b_ref_ids)

#                 transition_floor_ids.add(seg_a.floor_id)
#                 transition_floor_ids.add(seg_b.floor_id)

#             if transition_shared_ids or transition_connector_ids:
#                 vc_query = {"status": "active"}
#                 or_clauses = []
#                 if transition_connector_ids:
#                     or_clauses.append({"connector_id": {"$in": list(transition_connector_ids)}})
#                 if transition_shared_ids:
#                     or_clauses.append({"shared_id": {"$in": list(transition_shared_ids)}})
#                 if or_clauses:
#                     vc_query["$or"] = or_clauses
#                 if transition_floor_ids:
#                     vc_query["floor_id"] = {"$in": list(transition_floor_ids)}
#                 vcs = await VerticalConnector.find(vc_query).to_list()
#                 # Deduplicate by connector_id
#                 seen = set()
#                 for vc in vcs:
#                     if vc.connector_id not in seen:
#                         vertical_connectors.append(_dump_without_object_id(vc))
#                         seen.add(vc.connector_id)

#         # Floors details for floors referenced in the path
#         floors_details = []
#         if floor_ids:
#             floors_docs = await Floor.find({"floor_id": {"$in": list(floor_ids)}, "status": "active"}).to_list()
#             floors_details = [_dump_without_object_id(f) for f in floors_docs]

#         item = PathDetail(
#             path_id=path.path_id,
#             name=path.name,
#             building_id=path.building_id,
#             created_by=path.created_by,
#             start_point_id=path.start_point_id,
#             end_point_id=path.end_point_id,
#             start_point=_dump_without_object_id(start_location),
#             end_point=_dump_without_object_id(end_location),
#             is_published=path.is_published,
#             is_multifloor=path.is_multifloor,
#             floors=path.floors or [],
#             connector_shared_ids=path.connector_shared_ids or [],
#             floors_details=floors_details,
#             vertical_connectors=vertical_connectors,
#             floor_segments=[s.model_dump() for s in (path.floor_segments or [])],
#             tags=path.tags or [],
#             datetime=path.datetime,
#             status=path.status,
#         )

#         return {
#             "status": "success",
#             "message": "Path retrieved successfully",
#             "data": item,
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception(f"Error retrieving path '{path_id}': {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve path: {str(e)}",
#         )


# from fastapi import HTTPException, Path as FastAPIPath, status, Query
# from fastapi.responses import JSONResponse
# from pydantic import BaseModel
# from typing import Optional, List, Dict, Any
# import logging
# import time
# import hashlib
# import asyncio

# from src.datamodel.database.domain.DigitalSignage import Path, Location, VerticalConnector, Floor, NodeKind
# from src.datamodel.datavalidation.apiconfig import ApiConfig
# from src.common.redis_utils import get_cache_fast, set_cache_fast, get_compressed_cache, set_cache_background

# logger = logging.getLogger(__name__)

# # Ultra-fast in-memory cache for paths (most frequently accessed)
# _PATH_MEMORY_CACHE: Dict[str, Dict] = {}
# _PATH_CACHE_ACCESS_ORDER = []
# MAX_PATH_MEMORY_CACHE = 50  # Smaller cache for detailed data

# def add_to_path_memory_cache(key: str, data: Dict):
#     """Ultra-fast in-memory cache for path data"""
#     global _PATH_MEMORY_CACHE, _PATH_CACHE_ACCESS_ORDER
    
#     if key in _PATH_MEMORY_CACHE:
#         _PATH_CACHE_ACCESS_ORDER.remove(key)
#     elif len(_PATH_MEMORY_CACHE) >= MAX_PATH_MEMORY_CACHE:
#         # Remove oldest entry
#         oldest = _PATH_CACHE_ACCESS_ORDER.pop(0)
#         del _PATH_MEMORY_CACHE[oldest]
    
#     _PATH_MEMORY_CACHE[key] = data
#     _PATH_CACHE_ACCESS_ORDER.append(key)

# def get_from_path_memory_cache(key: str) -> Optional[Dict]:
#     """Get from path in-memory cache"""
#     if key in _PATH_MEMORY_CACHE:
#         # Move to end (most recently used)
#         _PATH_CACHE_ACCESS_ORDER.remove(key)
#         _PATH_CACHE_ACCESS_ORDER.append(key)
#         return _PATH_MEMORY_CACHE[key]
#     return None

# def _dump_without_object_id(doc):
#     """Optimized document dumping without ObjectId"""
#     if not doc:
#         return None
#     try:
#         # Use model_dump with exclude for better performance
#         return doc.model_dump(exclude={"id"})
#     except Exception:
#         # Fallback method
#         d = doc.model_dump()
#         d.pop("id", None)
#         return d

# def _dump_without_object_id_batch(docs: List) -> List[Dict]:
#     """Batch process multiple documents for better performance"""
#     if not docs:
#         return []
    
#     result = []
#     for doc in docs:
#         try:
#             dumped = doc.model_dump(exclude={"id"})
#             result.append(dumped)
#         except Exception:
#             d = doc.model_dump()
#             d.pop("id", None)
#             result.append(d)
#     return result

# def generate_path_cache_key(path_id: str, include_details: bool = True) -> str:
#     """Generate optimized cache key for paths"""
#     # Use shorter key format
#     suffix = "full" if include_details else "light"
#     return f"p:{path_id[-12:]}:{suffix}"  # "p:" prefix for path

# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Path"],
#         "summary": "Get Path by ID",
#         "response_model": dict,
#         "description": "Get a specific navigation path by its ID with ultra-fast caching.",
#         "response_description": "Path details",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)

# class PathDetailLight(BaseModel):
#     """Lightweight path model for faster responses"""
#     path_id: str
#     name: Optional[str] = None
#     building_id: str
#     start_point_id: str
#     end_point_id: str
#     is_published: bool
#     is_multifloor: bool
#     floors: List[str] = []
#     status: str

# class PathDetail(BaseModel):
#     """Full path model with all details"""
#     path_id: str
#     name: Optional[str] = None
#     building_id: str
#     created_by: Optional[str] = None

#     start_point_id: str
#     end_point_id: str
#     start_point: Optional[dict] = None
#     end_point: Optional[dict] = None

#     is_published: bool
#     is_multifloor: bool
#     floors: List[str] = []
#     connector_shared_ids: List[str] = []
#     floors_details: List[dict] = []
#     vertical_connectors: List[dict] = []

#     floor_segments: List[dict]

#     tags: List[str] = []
#     datetime: float
#     status: str

# async def get_path_with_details_optimized(path_id: str, include_full_details: bool = True) -> Dict[str, Any]:
#     """Ultra-optimized path retrieval with concurrent queries"""
#     try:
#         # Main path query with timeout
#         path = await asyncio.wait_for(
#             Path.find_one({"path_id": path_id, "status": "active"}),
#             timeout=3.0
#         )
        
#         if not path:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Path with ID '{path_id}' not found",
#             )

#         # For light response, return minimal data quickly
#         if not include_full_details:
#             return {
#                 "status": "success",
#                 "message": "Path retrieved successfully",
#                 "data": PathDetailLight(
#                     path_id=path.path_id,
#                     name=path.name,
#                     building_id=path.building_id,
#                     start_point_id=path.start_point_id,
#                     end_point_id=path.end_point_id,
#                     is_published=path.is_published,
#                     is_multifloor=path.is_multifloor,
#                     floors=path.floors or [],
#                     status=path.status,
#                 )
#             }

#         # Prepare concurrent queries for full details
#         tasks = []
#         floor_ids = {seg.floor_id for seg in (path.floor_segments or [])}

#         # Task 1: Get start location
#         tasks.append(
#             Location.find_one({"location_id": path.start_point_id, "status": "active"})
#         )
        
#         # Task 2: Get end location
#         tasks.append(
#             Location.find_one({"location_id": path.end_point_id, "status": "active"})
#         )
        
#         # Task 3: Get floors details
#         if floor_ids:
#             tasks.append(
#                 Floor.find({"floor_id": {"$in": list(floor_ids)}, "status": "active"}).to_list()
#             )
#         else:
#             tasks.append(asyncio.sleep(0, result=[]))  # Dummy task

#         # Execute concurrent queries
#         start_location, end_location, floors_docs = await asyncio.gather(*tasks, return_exceptions=True)
        
#         # Handle exceptions from concurrent queries
#         if isinstance(start_location, Exception):
#             logger.warning(f"Failed to get start location: {start_location}")
#             start_location = None
#         if isinstance(end_location, Exception):
#             logger.warning(f"Failed to get end location: {end_location}")
#             end_location = None
#         if isinstance(floors_docs, Exception):
#             logger.warning(f"Failed to get floors: {floors_docs}")
#             floors_docs = []

#         # Process vertical connectors for multifloor paths
#         vertical_connectors = []
#         if path.is_multifloor:
#             vertical_connectors = await get_vertical_connectors_optimized(path)

#         # Build response efficiently
#         floors_details = _dump_without_object_id_batch(floors_docs) if floors_docs else []
        
#         # Create optimized floor segments (limit data if too large)
#         floor_segments = []
#         for seg in (path.floor_segments or []):
#             seg_data = seg.model_dump()
#             # Limit points array if too large for performance
#             if "points" in seg_data and len(seg_data["points"]) > 100:
#                 seg_data["points"] = seg_data["points"][:100]
#                 seg_data["points_truncated"] = True
#             floor_segments.append(seg_data)

#         item = PathDetail(
#             path_id=path.path_id,
#             name=path.name,
#             building_id=path.building_id,
#             created_by=path.created_by,
#             start_point_id=path.start_point_id,
#             end_point_id=path.end_point_id,
#             start_point=_dump_without_object_id(start_location),
#             end_point=_dump_without_object_id(end_location),
#             is_published=path.is_published,
#             is_multifloor=path.is_multifloor,
#             floors=path.floors or [],
#             connector_shared_ids=path.connector_shared_ids or [],
#             floors_details=floors_details,
#             vertical_connectors=vertical_connectors,
#             floor_segments=floor_segments,
#             tags=path.tags or [],
#             datetime=path.datetime,
#             status=path.status,
#         )

#         return {
#             "status": "success",
#             "message": "Path retrieved successfully",
#             "data": item,
#         }

#     except asyncio.TimeoutError:
#         logger.error(f"Timeout retrieving path: {path_id}")
#         raise HTTPException(status_code=504, detail="Path query timeout")
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error retrieving path '{path_id}': {str(e)}")
#         raise

# async def get_vertical_connectors_optimized(path) -> List[Dict]:
#     """Optimized vertical connector retrieval"""
#     try:
#         segments = sorted((path.floor_segments or []), key=lambda s: getattr(s, "sequence", 0))
#         transition_shared_ids = set()
#         transition_connector_ids = set()
#         transition_floor_ids = set()

#         def is_vc_point(pt):
#             kind_val = getattr(pt, "kind", None)
#             return kind_val == NodeKind.VERTICAL_CONNECTOR or str(kind_val) == "vertical_connector"

#         # Optimized loop with early termination
#         for i in range(min(len(segments) - 1, 20)):  # Limit iterations for performance
#             seg_a = segments[i]
#             seg_b = segments[i + 1]
            
#             if seg_a.floor_id == seg_b.floor_id:
#                 continue
                
#             # Process points more efficiently
#             a_points = seg_a.points or []
#             b_points = seg_b.points or []
            
#             a_shared = {getattr(p, "shared_id", None) for p in a_points[:50] if is_vc_point(p)}  # Limit points
#             b_shared = {getattr(p, "shared_id", None) for p in b_points[:50] if is_vc_point(p)}
#             a_shared.discard(None)
#             b_shared.discard(None)
            
#             common_shared = a_shared & b_shared
#             if common_shared:
#                 transition_shared_ids.update(common_shared)
#             else:
#                 transition_shared_ids.update(a_shared | b_shared)

#             a_ref_ids = {getattr(p, "ref_id", None) for p in a_points[:50] if is_vc_point(p)}
#             b_ref_ids = {getattr(p, "ref_id", None) for p in b_points[:50] if is_vc_point(p)}
#             a_ref_ids.discard(None)
#             b_ref_ids.discard(None)
            
#             transition_connector_ids.update(a_ref_ids | b_ref_ids)
#             transition_floor_ids.add(seg_a.floor_id)
#             transition_floor_ids.add(seg_b.floor_id)

#         # Query vertical connectors if we have IDs
#         if transition_shared_ids or transition_connector_ids:
#             vc_query = {"status": "active"}
#             or_clauses = []
            
#             if transition_connector_ids:
#                 or_clauses.append({"connector_id": {"$in": list(transition_connector_ids)[:20]}})  # Limit query size
#             if transition_shared_ids:
#                 or_clauses.append({"shared_id": {"$in": list(transition_shared_ids)[:20]}})
            
#             if or_clauses:
#                 vc_query["$or"] = or_clauses
#             if transition_floor_ids:
#                 vc_query["floor_id"] = {"$in": list(transition_floor_ids)[:10]}  # Limit floors

#             vcs = await asyncio.wait_for(
#                 VerticalConnector.find(vc_query).limit(20).to_list(),  # Limit results
#                 timeout=2.0
#             )
            
#             # Deduplicate efficiently
#             seen = set()
#             vertical_connectors = []
#             for vc in vcs:
#                 if vc.connector_id not in seen:
#                     vertical_connectors.append(_dump_without_object_id(vc))
#                     seen.add(vc.connector_id)
#                     if len(vertical_connectors) >= 10:  # Limit results
#                         break
            
#             return vertical_connectors

#         return []
        
#     except Exception as e:
#         logger.warning(f"Error getting vertical connectors: {e}")
#         return []

# async def main(
#     path_id: str = FastAPIPath(..., description="Path ID to retrieve"),
#     light: bool = Query(False, description="Return minimal data for faster response"),
#     no_cache: bool = Query(False, description="Skip cache for debugging"),
# ):
#     """Ultra-optimized path retrieval endpoint"""
#     start_time = time.perf_counter()
    
#     # Generate cache key
#     cache_key = generate_path_cache_key(path_id, include_details=not light)
    
#     if not no_cache:
#         # Layer 1: Check in-memory cache first
#         memory_start = time.perf_counter()
#         cached_data = get_from_path_memory_cache(cache_key)
#         if cached_data:
#             memory_time = (time.perf_counter() - memory_start) * 1000
#             total_time = (time.perf_counter() - start_time) * 1000
#             logger.info(f"PATH MEMORY HIT: {path_id} | Memory: {memory_time:.1f}ms | Total: {total_time:.1f}ms")
            
#             return JSONResponse(
#                 content=cached_data,
#                 headers={"X-Cache": "MEMORY", "X-Response-Time": f"{total_time:.1f}ms"}
#             )

#         # Layer 2: Check Redis cache
#         redis_start = time.perf_counter()
#         try:
#             cached_data = await get_cache_fast(cache_key)
            
#             if cached_data:
#                 redis_time = (time.perf_counter() - redis_start) * 1000
#                 total_time = (time.perf_counter() - start_time) * 1000
                
#                 # Add to memory cache for next time
#                 add_to_path_memory_cache(cache_key, cached_data)
                
#                 logger.info(f"PATH REDIS HIT: {path_id} | Redis: {redis_time:.1f}ms | Total: {total_time:.1f}ms")
                
#                 return JSONResponse(
#                     content=cached_data,
#                     headers={"X-Cache": "REDIS", "X-Response-Time": f"{total_time:.1f}ms"}
#                 )
#         except Exception as e:
#             logger.warning(f"Redis cache failed for path {path_id}: {e}")

#         redis_time = (time.perf_counter() - redis_start) * 1000
#         logger.info(f"PATH CACHE MISS: {path_id} | Cache check: {redis_time:.1f}ms")

#     # Layer 3: Database query
#     try:
#         db_start = time.perf_counter()
#         response = await get_path_with_details_optimized(path_id, include_full_details=not light)
#         db_time = (time.perf_counter() - db_start) * 1000

#         # Cache the response asynchronously (don't block)
#         if not no_cache:
#             cache_ttl = 1800 if light else 3600  # 30min for light, 1hr for full
#             set_cache_background(cache_key, response, expire=cache_ttl)
            
#             # Add to memory cache immediately
#             add_to_path_memory_cache(cache_key, response)

#         total_time = (time.perf_counter() - start_time) * 1000
#         logger.info(f"PATH DB QUERY: {path_id} | DB: {db_time:.1f}ms | Total: {total_time:.1f}ms")

#         return JSONResponse(
#             content=response,
#             headers={
#                 "X-Cache": "MISS",
#                 "X-Response-Time": f"{total_time:.1f}ms",
#                 "X-DB-Time": f"{db_time:.1f}ms"
#             }
#         )

#     except HTTPException:
#         raise
#     except Exception as e:
#         total_time = (time.perf_counter() - start_time) * 1000
#         logger.exception(f"Error retrieving path '{path_id}': {str(e)} | Time: {total_time:.1f}ms")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve path: {str(e)}",
#         )

# # Utility functions for cache management
# async def warm_path_cache(path_ids: List[str]):
#     """Pre-warm cache for frequently accessed paths"""
#     for path_id in path_ids[:10]:  # Limit warming
#         try:
#             cache_key = generate_path_cache_key(path_id)
#             if not get_from_path_memory_cache(cache_key):
#                 logger.info(f"Warming path cache for {path_id}")
#                 # You can call the main function here to warm the cache
#                 # await get_path_with_details_optimized(path_id)
#         except Exception as e:
#             logger.warning(f"Failed to warm cache for path {path_id}: {e}")

# async def get_path_cache_stats():
#     """Get path cache performance statistics"""
#     return {
#         "path_memory_cache_size": len(_PATH_MEMORY_CACHE),
#         "path_cache_keys": _PATH_CACHE_ACCESS_ORDER[-5:],  # Last 5 keys
#         "path_memory_cache_max": MAX_PATH_MEMORY_CACHE
#     }


from fastapi import HTTPException, Path as FastAPIPath, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import time
import hashlib
import asyncio

from src.datamodel.database.domain.DigitalSignage import Path, Location, VerticalConnector, Floor, NodeKind
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.common.redis_utils import get_cache_fast, set_cache_fast, get_compressed_cache, set_cache_background

logger = logging.getLogger(__name__)

# Ultra-fast in-memory cache for paths (most frequently accessed)
_PATH_MEMORY_CACHE: Dict[str, Dict] = {}
_PATH_CACHE_ACCESS_ORDER = []
MAX_PATH_MEMORY_CACHE = 50  # Smaller cache for detailed data

def add_to_path_memory_cache(key: str, data: Dict):
    """Ultra-fast in-memory cache for path data"""
    global _PATH_MEMORY_CACHE, _PATH_CACHE_ACCESS_ORDER
    
    if key in _PATH_MEMORY_CACHE:
        _PATH_CACHE_ACCESS_ORDER.remove(key)
    elif len(_PATH_MEMORY_CACHE) >= MAX_PATH_MEMORY_CACHE:
        # Remove oldest entry
        oldest = _PATH_CACHE_ACCESS_ORDER.pop(0)
        del _PATH_MEMORY_CACHE[oldest]
    
    _PATH_MEMORY_CACHE[key] = data
    _PATH_CACHE_ACCESS_ORDER.append(key)

def get_from_path_memory_cache(key: str) -> Optional[Dict]:
    """Get from path in-memory cache"""
    if key in _PATH_MEMORY_CACHE:
        # Move to end (most recently used)
        _PATH_CACHE_ACCESS_ORDER.remove(key)
        _PATH_CACHE_ACCESS_ORDER.append(key)
        return _PATH_MEMORY_CACHE[key]
    return None

def _dump_without_object_id(doc):
    """Optimized document dumping without ObjectId"""
    if not doc:
        return None
    try:
        # Use model_dump with exclude for better performance
        return doc.model_dump(exclude={"id"})
    except Exception:
        # Fallback method
        d = doc.model_dump()
        d.pop("id", None)
        return d

def _dump_without_object_id_batch(docs: List) -> List[Dict]:
    """Batch process multiple documents for better performance"""
    if not docs:
        return []
    
    result = []
    for doc in docs:
        try:
            dumped = doc.model_dump(exclude={"id"})
            result.append(dumped)
        except Exception:
            d = doc.model_dump()
            d.pop("id", None)
            result.append(d)
    return result

def generate_path_cache_key(path_id: str, include_details: bool = True) -> str:
    """Generate optimized cache key for paths"""
    # Use shorter key format
    suffix = "full" if include_details else "light"
    return f"p:{path_id[-12:]}:{suffix}"  # "p:" prefix for path

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Path"],
        "summary": "Get Path by ID",
        "response_model": dict,
        "description": "Get a specific navigation path by its ID with ultra-fast caching.",
        "response_description": "Path details",
        "deprecated": False,
    }
    return ApiConfig(**config)

class PathDetailLight(BaseModel):
    """Lightweight path model for faster responses"""
    path_id: str
    name: Optional[str] = None
    building_id: str
    start_point_id: str
    end_point_id: str
    is_published: bool
    is_multifloor: bool
    floors: List[str] = []
    status: str

class PathDetail(BaseModel):
    """Full path model with all details"""
    path_id: str
    name: Optional[str] = None
    building_id: str
    created_by: Optional[str] = None

    start_point_id: str
    end_point_id: str
    start_point: Optional[dict] = None
    end_point: Optional[dict] = None

    is_published: bool
    is_multifloor: bool
    floors: List[str] = []
    connector_shared_ids: List[str] = []
    floors_details: List[dict] = []
    vertical_connectors: List[dict] = []

    floor_segments: List[dict]

    tags: List[str] = []
    datetime: float
    status: str

async def get_path_with_details_optimized(path_id: str, include_full_details: bool = True) -> Dict[str, Any]:
    """Ultra-optimized path retrieval with concurrent queries"""
    try:
        # Main path query with timeout
        path = await asyncio.wait_for(
            Path.find_one({"path_id": path_id, "status": "active"}),
            timeout=3.0
        )
        
        if not path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path with ID '{path_id}' not found",
            )

        # For light response, return minimal data quickly
        if not include_full_details:
            light_model = PathDetailLight(
                path_id=path.path_id,
                name=path.name,
                building_id=path.building_id,
                start_point_id=path.start_point_id,
                end_point_id=path.end_point_id,
                is_published=path.is_published,
                is_multifloor=path.is_multifloor,
                floors=path.floors or [],
                status=path.status,
            )
            return {
                "status": "success",
                "message": "Path retrieved successfully",
                "data": light_model.model_dump(),  # Convert to dict
            }

        # Prepare concurrent queries for full details
        tasks = []
        floor_ids = {seg.floor_id for seg in (path.floor_segments or [])}

        # Task 1: Get start location
        tasks.append(
            Location.find_one({"location_id": path.start_point_id, "status": "active"})
        )
        
        # Task 2: Get end location
        tasks.append(
            Location.find_one({"location_id": path.end_point_id, "status": "active"})
        )
        
        # Task 3: Get floors details
        if floor_ids:
            tasks.append(
                Floor.find({"floor_id": {"$in": list(floor_ids)}, "status": "active"}).to_list()
            )
        else:
            tasks.append(asyncio.sleep(0, result=[]))  # Dummy task

        # Execute concurrent queries
        start_location, end_location, floors_docs = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions from concurrent queries
        if isinstance(start_location, Exception):
            logger.warning(f"Failed to get start location: {start_location}")
            start_location = None
        if isinstance(end_location, Exception):
            logger.warning(f"Failed to get end location: {end_location}")
            end_location = None
        if isinstance(floors_docs, Exception):
            logger.warning(f"Failed to get floors: {floors_docs}")
            floors_docs = []

        # Process vertical connectors for multifloor paths
        vertical_connectors = []
        if path.is_multifloor:
            vertical_connectors = await get_vertical_connectors_optimized(path)

        # Build response efficiently
        floors_details = _dump_without_object_id_batch(floors_docs) if floors_docs else []
        
        # Create optimized floor segments (limit data if too large)
        floor_segments = []
        for seg in (path.floor_segments or []):
            seg_data = seg.model_dump()
            # Limit points array if too large for performance
            if "points" in seg_data and len(seg_data["points"]) > 100:
                seg_data["points"] = seg_data["points"][:100]
                seg_data["points_truncated"] = True
            floor_segments.append(seg_data)

        # Create the model and convert to dict immediately
        item = PathDetail(
            path_id=path.path_id,
            name=path.name,
            building_id=path.building_id,
            created_by=path.created_by,
            start_point_id=path.start_point_id,
            end_point_id=path.end_point_id,
            start_point=_dump_without_object_id(start_location),
            end_point=_dump_without_object_id(end_location),
            is_published=path.is_published,
            is_multifloor=path.is_multifloor,
            floors=path.floors or [],
            connector_shared_ids=path.connector_shared_ids or [],
            floors_details=floors_details,
            vertical_connectors=vertical_connectors,
            floor_segments=floor_segments,
            tags=path.tags or [],
            datetime=path.datetime,
            status=path.status,
        )

        return {
            "status": "success",
            "message": "Path retrieved successfully",
            "data": item.model_dump(),  # Convert to dict here
        }

    except asyncio.TimeoutError:
        logger.error(f"Timeout retrieving path: {path_id}")
        raise HTTPException(status_code=504, detail="Path query timeout")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving path '{path_id}': {str(e)}")
        raise

async def get_vertical_connectors_optimized(path) -> List[Dict]:
    """Optimized vertical connector retrieval"""
    try:
        segments = sorted((path.floor_segments or []), key=lambda s: getattr(s, "sequence", 0))
        transition_shared_ids = set()
        transition_connector_ids = set()
        transition_floor_ids = set()

        def is_vc_point(pt):
            kind_val = getattr(pt, "kind", None)
            return kind_val == NodeKind.VERTICAL_CONNECTOR or str(kind_val) == "vertical_connector"

        # Optimized loop with early termination
        for i in range(min(len(segments) - 1, 20)):  # Limit iterations for performance
            seg_a = segments[i]
            seg_b = segments[i + 1]
            
            if seg_a.floor_id == seg_b.floor_id:
                continue
                
            # Process points more efficiently
            a_points = seg_a.points or []
            b_points = seg_b.points or []
            
            a_shared = {getattr(p, "shared_id", None) for p in a_points[:50] if is_vc_point(p)}  # Limit points
            b_shared = {getattr(p, "shared_id", None) for p in b_points[:50] if is_vc_point(p)}
            a_shared.discard(None)
            b_shared.discard(None)
            
            common_shared = a_shared & b_shared
            if common_shared:
                transition_shared_ids.update(common_shared)
            else:
                transition_shared_ids.update(a_shared | b_shared)

            a_ref_ids = {getattr(p, "ref_id", None) for p in a_points[:50] if is_vc_point(p)}
            b_ref_ids = {getattr(p, "ref_id", None) for p in b_points[:50] if is_vc_point(p)}
            a_ref_ids.discard(None)
            b_ref_ids.discard(None)
            
            transition_connector_ids.update(a_ref_ids | b_ref_ids)
            transition_floor_ids.add(seg_a.floor_id)
            transition_floor_ids.add(seg_b.floor_id)

        # Query vertical connectors if we have IDs
        if transition_shared_ids or transition_connector_ids:
            vc_query = {"status": "active"}
            or_clauses = []
            
            if transition_connector_ids:
                or_clauses.append({"connector_id": {"$in": list(transition_connector_ids)[:20]}})  # Limit query size
            if transition_shared_ids:
                or_clauses.append({"shared_id": {"$in": list(transition_shared_ids)[:20]}})
            
            if or_clauses:
                vc_query["$or"] = or_clauses
            if transition_floor_ids:
                vc_query["floor_id"] = {"$in": list(transition_floor_ids)[:10]}  # Limit floors

            vcs = await asyncio.wait_for(
                VerticalConnector.find(vc_query).limit(20).to_list(),  # Limit results
                timeout=2.0
            )
            
            # Deduplicate efficiently
            seen = set()
            vertical_connectors = []
            for vc in vcs:
                if vc.connector_id not in seen:
                    vertical_connectors.append(_dump_without_object_id(vc))
                    seen.add(vc.connector_id)
                    if len(vertical_connectors) >= 10:  # Limit results
                        break
            
            return vertical_connectors

        return []
        
    except Exception as e:
        logger.warning(f"Error getting vertical connectors: {e}")
        return []

async def main(
    path_id: str = FastAPIPath(..., description="Path ID to retrieve"),
    light: bool = Query(False, description="Return minimal data for faster response"),
    no_cache: bool = Query(False, description="Skip cache for debugging"),
):
    """Ultra-optimized path retrieval endpoint"""
    start_time = time.perf_counter()
    
    # Generate cache key
    cache_key = generate_path_cache_key(path_id, include_details=not light)
    
    if not no_cache:
        # Layer 1: Check in-memory cache first
        memory_start = time.perf_counter()
        cached_data = get_from_path_memory_cache(cache_key)
        if cached_data:
            memory_time = (time.perf_counter() - memory_start) * 1000
            total_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"PATH MEMORY HIT: {path_id} | Memory: {memory_time:.1f}ms | Total: {total_time:.1f}ms")
            
            return JSONResponse(
                content=cached_data,
                headers={"X-Cache": "MEMORY", "X-Response-Time": f"{total_time:.1f}ms"}
            )

        # Layer 2: Check Redis cache
        redis_start = time.perf_counter()
        try:
            cached_data = await get_cache_fast(cache_key)
            
            if cached_data:
                redis_time = (time.perf_counter() - redis_start) * 1000
                total_time = (time.perf_counter() - start_time) * 1000
                
                # Add to memory cache for next time
                add_to_path_memory_cache(cache_key, cached_data)
                
                logger.info(f"PATH REDIS HIT: {path_id} | Redis: {redis_time:.1f}ms | Total: {total_time:.1f}ms")
                
                return JSONResponse(
                    content=cached_data,
                    headers={"X-Cache": "REDIS", "X-Response-Time": f"{total_time:.1f}ms"}
                )
        except Exception as e:
            logger.warning(f"Redis cache failed for path {path_id}: {e}")

        redis_time = (time.perf_counter() - redis_start) * 1000
        logger.info(f"PATH CACHE MISS: {path_id} | Cache check: {redis_time:.1f}ms")

    # Layer 3: Database query
    try:
        db_start = time.perf_counter()
        response = await get_path_with_details_optimized(path_id, include_full_details=not light)
        db_time = (time.perf_counter() - db_start) * 1000

        # Cache the response asynchronously (don't block)
        if not no_cache:
            cache_ttl = 1800 if light else 3600  # 30min for light, 1hr for full
            set_cache_background(cache_key, response, expire=cache_ttl)
            
            # Add to memory cache immediately
            add_to_path_memory_cache(cache_key, response)

        total_time = (time.perf_counter() - start_time) * 1000
        logger.info(f"PATH DB QUERY: {path_id} | DB: {db_time:.1f}ms | Total: {total_time:.1f}ms")

        return JSONResponse(
            content=response,
            headers={
                "X-Cache": "MISS",
                "X-Response-Time": f"{total_time:.1f}ms",
                "X-DB-Time": f"{db_time:.1f}ms"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        total_time = (time.perf_counter() - start_time) * 1000
        logger.exception(f"Error retrieving path '{path_id}': {str(e)} | Time: {total_time:.1f}ms")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve path: {str(e)}",
        )

# Utility functions for cache management
async def warm_path_cache(path_ids: List[str]):
    """Pre-warm cache for frequently accessed paths"""
    for path_id in path_ids[:10]:  # Limit warming
        try:
            cache_key = generate_path_cache_key(path_id)
            if not get_from_path_memory_cache(cache_key):
                logger.info(f"Warming path cache for {path_id}")
                # You can call the main function here to warm the cache
                # await get_path_with_details_optimized(path_id)
        except Exception as e:
            logger.warning(f"Failed to warm cache for path {path_id}: {e}")

async def get_path_cache_stats():
    """Get path cache performance statistics"""
    return {
        "path_memory_cache_size": len(_PATH_MEMORY_CACHE),
        "path_cache_keys": _PATH_CACHE_ACCESS_ORDER[-5:],  # Last 5 keys
        "path_memory_cache_max": MAX_PATH_MEMORY_CACHE
    }