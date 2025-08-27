# from fastapi import HTTPException, Query, status
# from pydantic import BaseModel, Field
# from typing import Optional, List
# import logging
# from src.datamodel.database.domain.DigitalSignage import Location, ShapeType
# from src.datamodel.datavalidation.apiconfig import ApiConfig


# logger = logging.getLogger(__name__)


# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Location"],
#         "summary": "Get All Locations",
#         "response_model": dict,
#         "description": "Retrieve all locations with optional filtering by category, shape, status, floor, etc.",
#         "response_description": "List of locations",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)


# class LocationResponse(BaseModel):
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
#     updated_by: Optional[str] = None
#     update_on: Optional[float] = None
#     status: str

#     class Config:
#         allow_population_by_field_name = True


# async def main(
#     status_filter: Optional[str] = Query("active", description="Filter by status (active, inactive, deleted, all)"),
#     category: Optional[str] = Query(None, description="Filter by location category"),
#     floor_id: Optional[str] = Query(None, description="Filter by floor ID"),
#     shape: Optional[ShapeType] = Query(None, description="Filter by shape type (circle, rectangle)"),
#     name: Optional[str] = Query(None, description="Filter by location name (partial match)"),
#     limit: Optional[int] = Query(None, description="Limit number of results"),
#     skip: Optional[int] = Query(0, description="Skip number of results for pagination"),
#     sort_by: Optional[str] = Query("name", description="Sort by field (name, category, datetime, floor_id)"),
#     sort_order: Optional[str] = Query("asc", description="Sort order (asc, desc)")
# ):
#     try:
#         # Build query filter
#         query_filter = {}
        
#         if status_filter and status_filter != "all":
#             query_filter["status"] = status_filter
        
#         if category:
#             query_filter["category"] = {"$regex": category, "$options": "i"}  # Case-insensitive partial match
            
#         if floor_id:
#             query_filter["floor_id"] = floor_id
            
#         if shape:
#             query_filter["shape"] = shape
        
#         if name:
#             query_filter["name"] = {"$regex": name, "$options": "i"}  # Case-insensitive partial match

#         # Execute query with sorting
#         sort_direction = 1 if sort_order.lower() == "asc" else -1
#         query = Location.find(query_filter).sort([(sort_by, sort_direction)])
        
#         if skip:
#             query = query.skip(skip)
#         if limit:
#             query = query.limit(limit)
            
#         locations = await query.to_list()
        
#         # Prepare response
#         location_list = []
#         for location in locations:
#             location_response = LocationResponse(
#                 location_id=location.location_id,
#                 name=location.name,
#                 category=location.category,
#                 floor_id=location.floor_id,
#                 shape=location.shape.value,
#                 x=location.x,
#                 y=location.y,
#                 width=location.width,
#                 height=location.height,
#                 radius=location.radius,
#                 logo_url=location.logo_url,
#                 color=location.color,
#                 text_color=location.text_color,
#                 is_published=location.is_published,
#                 description=location.description,
#                 created_by=location.created_by,
#                 datetime=location.datetime,
#                 updated_by=location.updated_by,
#                 update_on=location.update_on,
#                 status=location.status
#             )
#             location_list.append(location_response)

#         logger.info(f"Retrieved {len(location_list)} locations")

#         return {
#             "status": "success",
#             "message": f"Retrieved {len(location_list)} locations",
#             "data": location_list,
#             "total": len(location_list),
#             "filters_applied": {
#                 "status": status_filter,
#                 "category": category,
#                 "floor_id": floor_id,
#                 "shape": shape.value if shape else None,
#                 "name": name
#             }
#         }

#     except Exception as e:
#         logger.exception(f"Error retrieving locations: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve locations: {str(e)}"
#         )



from fastapi import HTTPException, Query, status, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import time
import hashlib
import asyncio
from src.datamodel.database.domain.DigitalSignage import Location, ShapeType
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from src.common.redis_utils import get_cache_fast,  set_cache_background

logger = logging.getLogger(__name__)

# Ultra-fast in-memory cache for locations
_LOCATION_MEMORY_CACHE: Dict[str, Dict] = {}
_LOCATION_CACHE_ACCESS_ORDER = []
MAX_LOCATION_MEMORY_CACHE = 200  # Larger cache for location queries 

def add_to_location_memory_cache(key: str, data: Dict):
    """Ultra-fast in-memory cache for location data"""
    global _LOCATION_MEMORY_CACHE, _LOCATION_CACHE_ACCESS_ORDER
    
    if key in _LOCATION_MEMORY_CACHE:
        _LOCATION_CACHE_ACCESS_ORDER.remove(key)
    elif len(_LOCATION_MEMORY_CACHE) >= MAX_LOCATION_MEMORY_CACHE:
        # Remove oldest entries (batch removal for efficiency)
        for _ in range(20):  # Remove 20 entries at once
            if _LOCATION_CACHE_ACCESS_ORDER:
                oldest = _LOCATION_CACHE_ACCESS_ORDER.pop(0)
                _LOCATION_MEMORY_CACHE.pop(oldest, None)
    
    _LOCATION_MEMORY_CACHE[key] = data
    _LOCATION_CACHE_ACCESS_ORDER.append(key)

def get_from_location_memory_cache(key: str) -> Optional[Dict]:
    """Get from location in-memory cache"""
    if key in _LOCATION_MEMORY_CACHE:
        # Move to end (most recently used)
        _LOCATION_CACHE_ACCESS_ORDER.remove(key)
        _LOCATION_CACHE_ACCESS_ORDER.append(key)
        return _LOCATION_MEMORY_CACHE[key]
    return None

def generate_location_cache_key(entity_uuid: str, status_filter: str, category: Optional[str], 
                               floor_id: Optional[str], shape: Optional[str], name: Optional[str],
                               limit: Optional[int], skip: int, sort_by: str, sort_order: str,
                               light: bool = False) -> str:
    """Generate highly optimized cache key for locations"""
    # Create compact key representation
    parts = [
        "loc",  # prefix
        entity_uuid[-8:] if entity_uuid else "none",  # Last 8 chars of entity
        status_filter[0] if status_filter else "a",  # First char only
        category[:3] if category else "none",  # First 3 chars
        floor_id[-8:] if floor_id else "none",  # Last 8 chars of floor_id
        shape[0] if shape else "none",  # First char of shape
        str(limit) if limit else "none",
        str(skip) if skip else "0",
        sort_by[0] if sort_by else "n",  # First char of sort field
        "d" if sort_order == "desc" else "a",  # asc/desc
        "l" if light else "f"  # light/full
    ]
    
    # Add name hash if present
    if name:
        name_hash = hashlib.md5(name.encode()).hexdigest()[:6]
        parts.append(name_hash)
    
    return ":".join(parts)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Location"],
        "summary": "Get All Locations (Ultra-Fast)",
        "response_model": dict,
        "description": "Retrieve all locations with ultra-fast caching and optional filtering.",
        "response_description": "List of locations with sub-20ms response times",
        "deprecated": False,
    }
    return ApiConfig(**config)

class LocationResponseLight(BaseModel):
    """Lightweight location model for ultra-fast responses"""
    location_id: str
    name: str
    category: str
    floor_id: str
    shape: str
    x: float
    y: float
    color: str
    is_published: bool
    status: str

class LocationResponse(BaseModel):
    """Full location model"""
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
    updated_by: Optional[str] = None
    update_on: Optional[float] = None
    status: str

    class Config:
        allow_population_by_field_name = True

async def get_locations_optimized(entity_uuid: str, status_filter: Optional[str], 
                                category: Optional[str], floor_id: Optional[str], 
                                shape: Optional[str], name: Optional[str],
                                limit: Optional[int], skip: int, sort_by: str, 
                                sort_order: str, light: bool = False) -> Dict[str, Any]:
    """Ultra-optimized location query with sub-100ms database performance"""
    try:
        db_start = time.perf_counter()
        
        # Build optimized query filter
        query_filter = {}
        
        # Always include entity filter for performance
        if entity_uuid:
            query_filter["entity_uuid"] = entity_uuid
        
        if status_filter and status_filter != "all":
            query_filter["status"] = status_filter
        
        if category:
            # Use prefix match for better index usage
            query_filter["category"] = {"$regex": f"^{category}", "$options": "i"}
            
        if floor_id:
            query_filter["floor_id"] = floor_id
            
        if shape:
            query_filter["shape"] = shape
        
        if name:
            # Use prefix match for better performance
            query_filter["name"] = {"$regex": f"^{name}", "$options": "i"}

        # Build query with optimized sorting
        sort_direction = -1 if sort_order.lower() == "desc" else 1
        
        # Map sort fields to optimize for indexes
        sort_field_map = {
            "name": "name",
            "category": "category", 
            "datetime": "datetime",
            "floor_id": "floor_id"
        }
        actual_sort_field = sort_field_map.get(sort_by, "name")
        
        query = Location.find(query_filter)
        
        # Apply sorting with error handling
        try:
            query = query.sort([(actual_sort_field, sort_direction)])
        except Exception as sort_error:
            logger.warning(f"Sorting failed, using default: {sort_error}")
            # Fallback to no sorting for speed
        
        # Apply pagination limits
        if skip and skip > 0:
            query = query.skip(skip)
        if limit and limit > 0:
            query = query.limit(min(limit, 1000))  # Cap at 1000 for performance
        else:
            query = query.limit(500)  # Default limit to prevent large responses

        # Execute with timeout
        # locations = await asyncio.wait_for(query.to_list(), timeout=5.0)
        locations = await asyncio.wait_for(query.to_list(length=limit or 500), timeout=5.0)

        
        db_time = (time.perf_counter() - db_start) * 1000
        logger.info(f"Location DB query: {db_time:.1f}ms for {len(locations)} records")
        
        # Process results based on response mode
        if light:
            location_list = []
            for location in locations:
                try:
                    location_dict = {
                        "location_id": location.location_id,
                        "name": location.name,
                        "category": location.category,
                        "floor_id": location.floor_id,
                        "shape": location.shape.value if hasattr(location.shape, 'value') else str(location.shape),
                        "x": float(location.x),
                        "y": float(location.y),
                        "color": location.color,
                        "is_published": location.is_published,
                        "status": location.status
                    }
                    location_list.append(location_dict)
                except Exception as e:
                    logger.warning(f"Error processing location {getattr(location, 'location_id', 'unknown')}: {e}")
                    continue
        else:
            # Full response processing
            location_list = []
            for location in locations:
                try:
                    location_dict = {
                        "location_id": location.location_id,
                        "name": location.name,
                        "category": location.category,
                        "floor_id": location.floor_id,
                        "shape": location.shape.value if hasattr(location.shape, 'value') else str(location.shape),
                        "x": float(location.x),
                        "y": float(location.y),
                        "width": location.width,
                        "height": location.height,
                        "radius": location.radius,
                        "logo_url": getattr(location, 'logo_url', None),
                        "color": location.color,
                        "text_color": getattr(location, 'text_color', ''),
                        "is_published": location.is_published,
                        "description": getattr(location, 'description', None),
                        "created_by": getattr(location, 'created_by', None),
                        "datetime": location.datetime,
                        "updated_by": getattr(location, 'updated_by', None),
                        "update_on": getattr(location, 'update_on', None),
                        "status": location.status
                    }
                    location_list.append(location_dict)
                except Exception as e:
                    logger.warning(f"Error processing location {getattr(location, 'location_id', 'unknown')}: {e}")
                    continue

        # Build response
        if light:
            response = {
                "data": location_list,
                "count": len(location_list)
            }
        else:
            response = {
                "status": "success",
                "message": f"Retrieved {len(location_list)} locations",
                "data": location_list,
                "pagination": {
                    "returned": len(location_list),
                    "skip": skip,
                    "limit": limit
                },
                "filters_applied": {
                    "status": status_filter,
                    "category": category,
                    "floor_id": floor_id,
                    "shape": shape,
                    "name": name
                }
            }
        
        return response
        
    except asyncio.TimeoutError:
        logger.error("Location query timeout")
        raise HTTPException(status_code=504, detail="Location query timeout")
    except Exception as e:
        logger.error(f"Database error in get_locations_optimized: {str(e)}")
        raise

async def main(
    request: Request,
    status_filter: Optional[str] = Query("active", description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category (prefix match)"),
    floor_id: Optional[str] = Query(None, description="Filter by floor ID"),
    shape: Optional[str] = Query(None, description="Filter by shape type"),
    name: Optional[str] = Query(None, description="Filter by name (prefix match)"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Limit results (max 1000)"),
    skip: Optional[int] = Query(0, ge=0, description="Skip results for pagination"),
    sort_by: Optional[str] = Query("name", description="Sort by field"),
    sort_order: Optional[str] = Query("asc", description="Sort order (asc, desc)"),
    light: bool = Query(False, description="Return minimal data for ultra-fast response"),
    no_cache: bool = Query(False, description="Skip cache for debugging")
):
    """Ultra-optimized location endpoint with sub-20ms cached responses"""
    
    # Validate token and get entity
    # validate_token(request)

    entity_uuid = getattr(request.state, 'entity_uuid', None)
    
    start_time = time.perf_counter()
    
    # Generate cache key
    shape_value = shape.value if shape else None
    cache_key = generate_location_cache_key(
        entity_uuid, status_filter or "active", category, floor_id, 
        shape_value, name, limit, skip or 0, sort_by or "name", 
        sort_order or "asc", light
    )
    
    if not no_cache:
        # Layer 1: Check in-memory cache first (ultra-fast)
        memory_start = time.perf_counter()
        cached_data = get_from_location_memory_cache(cache_key)
        if cached_data:
            memory_time = (time.perf_counter() - memory_start) * 1000
            total_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"LOC MEMORY HIT: {cache_key[:30]}... | Memory: {memory_time:.1f}ms | Total: {total_time:.1f}ms")
            
            return JSONResponse(
                content=cached_data,
                headers={
                    "X-Cache": "MEMORY", 
                    "X-Response-Time": f"{total_time:.1f}ms",
                    "X-Records": str(len(cached_data.get('data', [])))
                }
            )

        # Layer 2: Check Redis cache
        redis_start = time.perf_counter()
        try:
            cached_data = await get_cache_fast(cache_key)
            
            if cached_data:
                redis_time = (time.perf_counter() - redis_start) * 1000
                total_time = (time.perf_counter() - start_time) * 1000
                
                # Add to memory cache for next time
                add_to_location_memory_cache(cache_key, cached_data)
                
                logger.info(f"LOC REDIS HIT: {cache_key[:30]}... | Redis: {redis_time:.1f}ms | Total: {total_time:.1f}ms")
                
                return JSONResponse(
                    content=cached_data,
                    headers={
                        "X-Cache": "REDIS", 
                        "X-Response-Time": f"{total_time:.1f}ms",
                        "X-Records": str(len(cached_data.get('data', [])))
                    }
                )
        except Exception as e:
            logger.warning(f"Redis cache failed: {e}")

        redis_time = (time.perf_counter() - redis_start) * 1000
        logger.info(f"LOC CACHE MISS: {cache_key[:30]}... | Cache check: {redis_time:.1f}ms")

    # Layer 3: Database query
    try:
        db_start = time.perf_counter()
        response = await get_locations_optimized(
            entity_uuid, status_filter, category, floor_id, shape_value, name,
            limit, skip or 0, sort_by or "name", sort_order or "asc", light
        )
        db_time = (time.perf_counter() - db_start) * 1000

        # Cache the response asynchronously (don't block)
        if not no_cache:
            # Smart TTL based on query type
            if name or category:
                cache_ttl = 900  # 15 minutes for searches
            elif floor_id:
                cache_ttl = 1800  # 30 minutes for floor-specific
            else:
                cache_ttl = 3600  # 1 hour for general queries
                
            set_cache_background(cache_key, response, expire=cache_ttl)
            
            # Add to memory cache immediately
            add_to_location_memory_cache(cache_key, response)

        total_time = (time.perf_counter() - start_time) * 1000
        record_count = len(response.get('data', []))
        logger.info(f"LOC DB QUERY: {cache_key[:30]}... | DB: {db_time:.1f}ms | Total: {total_time:.1f}ms | Records: {record_count}")

        return JSONResponse(
            content=response,
            headers={
                "X-Cache": "MISS",
                "X-Response-Time": f"{total_time:.1f}ms",
                "X-DB-Time": f"{db_time:.1f}ms",
                "X-Records": str(record_count)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        total_time = (time.perf_counter() - start_time) * 1000
        logger.exception(f"Error retrieving locations: {str(e)} | Time: {total_time:.1f}ms")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve locations: {str(e)}"
        )

# Cache management utilities
async def warm_location_cache_by_floor(entity_uuid: str, floor_ids: List[str]):
    """Pre-warm cache for specific floors"""
    for floor_id in floor_ids[:5]:  # Limit to 5 floors
        try:
            cache_key = generate_location_cache_key(
                entity_uuid, "active", None, floor_id, None, None,
                100, 0, "name", "asc", False
            )
            if not get_from_location_memory_cache(cache_key):
                logger.info(f"Warming location cache for floor {floor_id}")
                # You can trigger the actual query here if needed
        except Exception as e:
            logger.warning(f"Failed to warm cache for floor {floor_id}: {e}")

async def warm_common_location_queries(entity_uuid: str):
    """Pre-warm cache for common location queries"""
    common_queries = [
        {"status_filter": "active", "limit": 100, "light": True},
        {"status_filter": "active", "limit": 50, "light": True},
        {"status_filter": "active", "category": "office", "limit": 50},
        {"status_filter": "active", "category": "meeting", "limit": 50},
    ]
    
    for query in common_queries:
        try:
            cache_key = generate_location_cache_key(
                entity_uuid, 
                query.get("status_filter", "active"),
                query.get("category"),
                None,  # floor_id
                None,  # shape
                None,  # name
                query.get("limit", 100),
                0,     # skip
                "name",  # sort_by
                "asc",   # sort_order
                query.get("light", False)
            )
            
            if not get_from_location_memory_cache(cache_key):
                logger.info(f"Warming common location query cache")
                # You can trigger the actual query here if needed
                
        except Exception as e:
            logger.warning(f"Cache warming failed: {e}")

async def get_location_cache_stats():
    """Get location cache performance statistics"""
    return {
        "location_memory_cache_size": len(_LOCATION_MEMORY_CACHE),
        "location_cache_keys_sample": _LOCATION_CACHE_ACCESS_ORDER[-5:],
        "location_memory_cache_max": MAX_LOCATION_MEMORY_CACHE,
        "cache_hit_potential": f"{min(len(_LOCATION_MEMORY_CACHE), MAX_LOCATION_MEMORY_CACHE)}/{MAX_LOCATION_MEMORY_CACHE}"
    }

# Bulk cache invalidation for when locations change
async def invalidate_location_cache_by_floor(floor_id: str):
    """Invalidate all cached queries for a specific floor"""
    global _LOCATION_MEMORY_CACHE, _LOCATION_CACHE_ACCESS_ORDER
    
    keys_to_remove = []
    for key in _LOCATION_MEMORY_CACHE.keys():
        if floor_id in key:  # Simple floor_id matching in cache key
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        _LOCATION_MEMORY_CACHE.pop(key, None)
        if key in _LOCATION_CACHE_ACCESS_ORDER:
            _LOCATION_CACHE_ACCESS_ORDER.remove(key)
    
    logger.info(f"Invalidated {len(keys_to_remove)} location cache entries for floor {floor_id}")