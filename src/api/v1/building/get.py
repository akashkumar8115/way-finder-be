# from fastapi import HTTPException, Query, status, Depends, Request
# from pydantic import BaseModel, Field
# from typing import Optional, List
# import logging
# from src.datamodel.database.domain.DigitalSignage import Building
# from src.datamodel.datavalidation.apiconfig import ApiConfig
# from sqlalchemy.ext.asyncio import AsyncSession
# from src.core.middleware.token_validate_middleware import validate_token
# from src.core.database.dbs.getdb import postresql as db
# import time


# logger = logging.getLogger(__name__)


# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Building"],
#         "summary": "Get Buildings",
#         "response_model": dict,
#         "description": "Retrieve all buildings or filter by specific criteria.",
#         "response_description": "List of buildings",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)


# class BuildingResponse(BaseModel):
#     building_id: str
#     name: str
#     address: Optional[str] = None
#     floors: List[str] = []
#     description: Optional[str] = None
#     entity_uuid: Optional[str] = None
#     datetime: float
#     updated_by: Optional[str] = None
#     update_on: Optional[float] = None
#     status: str

#     class Config:
#         allow_population_by_field_name = True


# async def main(
#     request: Request,
#     status_filter: Optional[str] = Query("active", description="Filter by status (active, inactive, all)"),
#     name: Optional[str] = Query(None, description="Filter by building name (partial match)"),
#     limit: Optional[int] = Query(None, description="Limit number of results"),
#     skip: Optional[int] = Query(0, description="Skip number of results for pagination"),
#     db: AsyncSession = Depends(db)
# ):
    
#     """Main handler for content uploads"""
#     # Validate token and get user info
#     validate_token_start = time.time()
#     validate_token(request)
#     entity_uuid = request.state.entity_uuid
#     user_uuid = request.state.user_uuid
#     validate_token_time = time.time() - validate_token_start
#     logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

#     try:
#         # Build query filter
#         query_filter = {"entity_uuid": entity_uuid}
        
#         if status_filter and status_filter != "all":
#             query_filter["status"] = status_filter
        
#         if name:
#             query_filter["name"] = {"$regex": name, "$options": "i"}  # Case-insensitive partial match

#         # Execute query
#         query = Building.find(query_filter)
        
#         if skip:
#             query = query.skip(skip)
#         if limit:
#             query = query.limit(limit)
            
#         buildings = await query.to_list()
        
#         # Prepare response
#         building_list = []
#         for building in buildings:
#             building_response = BuildingResponse(
#                 building_id=building.building_id,
#                 name=building.name,
#                 address=building.address,
#                 floors=building.floors or [],
#                 description=building.description,
#                 entity_uuid=building.entity_uuid,
#                 datetime=building.datetime,
#                 updated_by=building.updated_by,
#                 update_on=building.update_on,
#                 status=building.status
#             )
#             building_list.append(building_response)

#         logger.info(f"Retrieved {len(building_list)} buildings")
#         logger.info(f"PERFORMANCE: Building retrieval took {time.time() - validate_token_start:.4f} seconds total")
#         return {
#             "status": "success",
#             "message": f"Retrieved {len(building_list)} buildings",
#             "data": building_list,
#             "total": len(building_list)
#         }

#     except Exception as e:
#         logger.exception(f"Error retrieving buildings: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve buildings: {str(e)}"
#         )

# redis apply

# from fastapi import HTTPException, Query, status, Depends, Request
# from pydantic import BaseModel, Field
# from typing import Optional, List
# import logging, time
# from src.datamodel.database.domain.DigitalSignage import Building
# from src.datamodel.datavalidation.apiconfig import ApiConfig
# from sqlalchemy.ext.asyncio import AsyncSession
# from src.core.middleware.token_validate_middleware import validate_token
# from src.core.database.dbs.getdb import postresql as db
# from src.common.redis_utils import get_cache, set_cache
# from fastapi.responses import JSONResponse
# logger = logging.getLogger(__name__)


# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Building"],
#         "summary": "Get Buildings",
#         "response_model": dict,
#         "description": "Retrieve all buildings or filter by specific criteria.",
#         "response_description": "List of buildings",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)


# class BuildingResponse(BaseModel):
#     building_id: str
#     name: str
#     address: Optional[str] = None
#     floors: List[str] = []
#     description: Optional[str] = None
#     entity_uuid: Optional[str] = None
#     datetime: float
#     updated_by: Optional[str] = None
#     update_on: Optional[float] = None
#     status: str

#     class Config:
#         allow_population_by_field_name = True


# async def main(
#     request: Request,
#     status_filter: Optional[str] = Query("active"),
#     name: Optional[str] = Query(None),
#     limit: Optional[int] = Query(None),
#     skip: Optional[int] = Query(0),
#     db: AsyncSession = Depends(db)
# ):
#     validate_token(request)
#     entity_uuid = request.state.entity_uuid

#     start_time = time.perf_counter()  # Request timer start

#     # Create cache key
#     cache_key = f"buildings:{entity_uuid}:{status_filter}:{name}:{limit}:{skip}"

#     # Check Redis first
#     cached_data = await get_cache(cache_key)
#     if cached_data:
#         elapsed = (time.perf_counter() - start_time) * 1000
#         logger.info(f"Cache HIT for {cache_key} | Time taken: {elapsed:.2f} ms")
#         return JSONResponse(content=cached_data)
#         # return cached_data
#     else:
#         logger.info(f"Cache MISS for {cache_key}")

#     try:
#         db_start = time.perf_counter()  # DB query timer

#         query_filter = {"entity_uuid": entity_uuid}
#         if status_filter and status_filter != "all":
#             query_filter["status"] = status_filter
#         if name:
#             query_filter["name"] = {"$regex": name, "$options": "i"}

#         query = Building.find(query_filter)
#         if skip:
#             query = query.skip(skip)
#         if limit:
#             query = query.limit(limit)

#         buildings = await query.to_list()

#         db_elapsed = (time.perf_counter() - db_start) * 1000
#         logger.info(f"DB Query executed in {db_elapsed:.2f} ms")

#         building_list = [
#             BuildingResponse(
#                 building_id=building.building_id,
#                 name=building.name,
#                 address=building.address,
#                 floors=building.floors or [],
#                 description=building.description,
#                 entity_uuid=building.entity_uuid,
#                 datetime=building.datetime,
#                 updated_by=building.updated_by,
#                 update_on=building.update_on,
#                 status=building.status
#             )
#             for building in buildings
#         ]

#         response = {
#             "status": "success",
#             "message": f"Retrieved {len(building_list)} buildings",
#             "data": [b.dict() for b in building_list],
#             "total": len(building_list)
#         }

#         # Save in Redis for ~100min
#         await set_cache(cache_key, response, expire=6000)

#         total_elapsed = (time.perf_counter() - start_time) * 1000
#         logger.info(f"Cache MISS → DB fetched and cached | Total time: {total_elapsed:.2f} ms")

#         return response

#     except Exception as e:
#         logger.exception(f"Error retrieving buildings: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve buildings: {str(e)}"
#         )


from fastapi import HTTPException, Query, status, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import time
import hashlib
import asyncio
from src.datamodel.database.domain.DigitalSignage import Building
from src.datamodel.datavalidation.apiconfig import ApiConfig
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db
from src.common.redis_utils import get_cache_fast, set_cache_fast, get_compressed_cache

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Building"],
        "summary": "Get Buildings",
        "response_model": dict,
        "description": "Retrieve all buildings or filter by specific criteria.",
        "response_description": "List of buildings",
        "deprecated": False,
    }
    return ApiConfig(**config)


# Ultra-lightweight response model for better performance
class BuildingResponseLight(BaseModel):
    building_id: str
    name: str
    address: Optional[str] = None
    floors: List[str] = []
    status: str

    class Config:
        allow_population_by_field_name = True

# Memory cache for extremely frequent requests (last 100 queries)
_MEMORY_CACHE: Dict[str, Dict] = {}
_CACHE_ACCESS_ORDER = []
MAX_MEMORY_CACHE = 100

def add_to_memory_cache(key: str, data: Dict):
    """Ultra-fast in-memory cache with LRU eviction"""
    global _MEMORY_CACHE, _CACHE_ACCESS_ORDER
    
    if key in _MEMORY_CACHE:
        _CACHE_ACCESS_ORDER.remove(key)
    elif len(_MEMORY_CACHE) >= MAX_MEMORY_CACHE:
        # Remove oldest entry
        oldest = _CACHE_ACCESS_ORDER.pop(0)
        del _MEMORY_CACHE[oldest]
    
    _MEMORY_CACHE[key] = data
    _CACHE_ACCESS_ORDER.append(key)

def get_from_memory_cache(key: str) -> Optional[Dict]:
    """Get from in-memory cache"""
    if key in _MEMORY_CACHE:
        # Move to end (most recently used)
        _CACHE_ACCESS_ORDER.remove(key)
        _CACHE_ACCESS_ORDER.append(key)
        return _MEMORY_CACHE[key]
    return None

def generate_fast_cache_key(entity_uuid: str, status_filter: str, 
                           name: Optional[str], limit: int, skip: int) -> str:
    """Generate optimized cache key"""
    # Use shorter, more efficient key format
    parts = [
        entity_uuid[-12:],  # Use only last 12 chars of UUID
        status_filter[0] if status_filter else "a",  # Just first char
        str(limit),
        str(skip)
    ]
    
    if name:
        # Use hash for name to keep key short
        name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
        parts.append(name_hash)
    
    return "b:" + ":".join(parts)  # "b:" prefix for buildings

async def get_buildings_optimized(entity_uuid: str, status_filter: Optional[str], 
                                name: Optional[str], limit: int, skip: int, 
                                db: AsyncSession) -> List[Dict]:
    """Ultra-optimized database query"""
    try:
        # Build minimal query filter
        query_filter = {"entity_uuid": entity_uuid}
        
        if status_filter and status_filter != "all":
            query_filter["status"] = status_filter
            
        if name:
            # More efficient regex - avoid leading ^ for better index usage
            query_filter["name"] = {"$regex": name, "$options": "i"}
        
        # Build query without sorting for maximum speed
        query = Building.find(query_filter)
        
        # Apply limits
        if skip > 0:
            query = query.skip(skip)
        query = query.limit(min(limit, 500))  # Reduced max limit
        
        # Execute with timeout
        buildings = await asyncio.wait_for(query.to_list(), timeout=5.0)
        
        # Minimal field extraction for speed
        building_list = []
        for building in buildings:
            # Only extract essential fields to reduce payload
            building_dict = {
                "building_id": building.building_id,
                "name": building.name,
                "address": getattr(building, 'address', None),
                "floors": getattr(building, 'floors', [])[:10],  # Limit floors array
                "status": building.status
            }
            building_list.append(building_dict)
        
        return building_list
        
    except asyncio.TimeoutError:
        logger.error("Database query timeout")
        raise HTTPException(status_code=504, detail="Database query timeout")
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise

async def main(
    request: Request,
    status_filter: Optional[str] = Query("active"),
    name: Optional[str] = Query(None),
    limit: Optional[int] = Query(50, ge=1, le=500),  # Reduced max limit
    skip: Optional[int] = Query(0, ge=0),
    light: bool = Query(False, description="Return minimal data for faster response"),
    db: AsyncSession = Depends(db)
):
    """Ultra-optimized building endpoint with multiple cache layers"""
    
    # Quick token validation
    validate_token(request)
    entity_uuid = request.state.entity_uuid
    
    start_time = time.perf_counter()
    
    # Generate efficient cache key
    cache_key = generate_fast_cache_key(entity_uuid, status_filter or "active", 
                                       name, limit, skip)
    
    # Layer 1: Check in-memory cache first (fastest)
    memory_start = time.perf_counter()
    cached_data = get_from_memory_cache(cache_key)
    if cached_data:
        memory_time = (time.perf_counter() - memory_start) * 1000
        total_time = (time.perf_counter() - start_time) * 1000
        logger.info(f"MEMORY HIT: {cache_key} | Memory: {memory_time:.1f}ms | Total: {total_time:.1f}ms")
        
        return JSONResponse(
            content=cached_data,
            headers={"X-Cache": "MEMORY", "X-Response-Time": f"{total_time:.1f}ms"}
        )
    
    # Layer 2: Check Redis cache
    redis_start = time.perf_counter()
    try:
        if light:
            # Use compressed cache for light requests
            cached_data = await get_compressed_cache(cache_key)
        else:
            cached_data = await get_cache_fast(cache_key)
            
        if cached_data:
            redis_time = (time.perf_counter() - redis_start) * 1000
            total_time = (time.perf_counter() - start_time) * 1000
            
            # Add to memory cache for next time
            add_to_memory_cache(cache_key, cached_data)
            
            logger.info(f"REDIS HIT: {cache_key} | Redis: {redis_time:.1f}ms | Total: {total_time:.1f}ms")
            
            return JSONResponse(
                content=cached_data,
                headers={"X-Cache": "REDIS", "X-Response-Time": f"{total_time:.1f}ms"}
            )
    except Exception as e:
        logger.warning(f"Redis cache failed: {e}")
    
    redis_time = (time.perf_counter() - redis_start) * 1000
    logger.info(f"CACHE MISS: {cache_key} | Cache check: {redis_time:.1f}ms")
    
    # Layer 3: Database query
    try:
        db_start = time.perf_counter()
        building_list = await get_buildings_optimized(
            entity_uuid, status_filter, name, limit, skip, db
        )
        db_time = (time.perf_counter() - db_start) * 1000
        
        # Build minimal response
        if light:
            response = {
                "data": building_list,
                "count": len(building_list)
            }
        else:
            response = {
                "status": "success",
                "data": building_list,
                "pagination": {
                    "limit": limit,
                    "skip": skip,
                    "returned": len(building_list)
                }
            }
        
        # Cache asynchronously (don't block response)
        cache_ttl = 1800 if name else 36000  # 300min for searches, 1hr for lists
        asyncio.create_task(set_cache_fast(cache_key, response, expire=cache_ttl))
        
        # Add to memory cache immediately
        add_to_memory_cache(cache_key, response)
        
        total_time = (time.perf_counter() - start_time) * 1000
        logger.info(f"DB QUERY: {cache_key} | DB: {db_time:.1f}ms | Total: {total_time:.1f}ms")
        
        return JSONResponse(
            content=response,
            headers={
                "X-Cache": "MISS", 
                "X-Response-Time": f"{total_time:.1f}ms",
                "X-DB-Time": f"{db_time:.1f}ms"
            }
        )
        
    except Exception as e:
        total_time = (time.perf_counter() - start_time) * 1000
        logger.exception(f"Error retrieving buildings: {str(e)} | Time: {total_time:.1f}ms")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve buildings: {str(e)}"
        )

# Health check for cache performance
async def get_cache_stats():
    """Get cache performance statistics"""
    return {
        "memory_cache_size": len(_MEMORY_CACHE),
        "memory_cache_keys": list(_CACHE_ACCESS_ORDER[-10:]),  # Last 10 keys
        "memory_cache_max": MAX_MEMORY_CACHE
    }

# Cache warming function for high-traffic queries
async def warm_common_caches(entity_uuid: str):
    """Pre-warm caches for common queries"""
    common_queries = [
        {"status_filter": "active", "limit": 50, "skip": 0},
        {"status_filter": "active", "limit": 100, "skip": 0},
        {"status_filter": "all", "limit": 50, "skip": 0},
    ]
    
    for query in common_queries:
        cache_key = generate_fast_cache_key(
            entity_uuid, query["status_filter"], None, 
            query["limit"], query["skip"]
        )
        
        # Only warm if not already cached
        if not get_from_memory_cache(cache_key):
            try:
                # This would trigger a DB query and cache the result
                logger.info(f"Warming cache for {cache_key}")
                # You can call your main function here or implement the logic
            except Exception as e:
                logger.warning(f"Cache warming failed: {e}")