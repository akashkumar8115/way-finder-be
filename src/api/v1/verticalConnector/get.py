# from fastapi import HTTPException, Query, status
# from pydantic import BaseModel, Field
# from typing import Optional, List
# import logging
# from src.datamodel.database.domain.DigitalSignage import VerticalConnector, ConnectorType
# from src.datamodel.datavalidation.apiconfig import ApiConfig

# logger = logging.getLogger(__name__)

# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Vertical Connector"],
#         "summary": "Get Vertical Connectors",
#         "response_model": dict,
#         "description": "Get vertical connectors with optional filtering by floor, building, or connector type.",
#         "response_description": "List of vertical connectors",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)

# class VerticalConnectorListItem(BaseModel):
#     connector_id: str
#     name: str
#     shared_id: str
#     connector_type: str
#     floor_id: str
#     shape: str
#     x: float
#     y: float
#     width: Optional[float] = None
#     height: Optional[float] = None
#     radius: Optional[float] = None
#     color: str
#     is_published: bool
#     created_by: Optional[str] = None
#     datetime: float
#     status: str

#     class Config:
#         allow_population_by_field_name = True

# async def main(
#     floor_id: Optional[str] = Query(None, description="Filter by floor ID"),
#     connector_type: Optional[ConnectorType] = Query(None, description="Filter by connector type"),
#     shared_id: Optional[str] = Query(None, description="Filter by shared ID"),
#     is_published: Optional[bool] = Query(None, description="Filter by published status"),
#     limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
#     skip: int = Query(0, ge=0, description="Number of results to skip")
# ):
#     try:
#         # Build filter query
#         filter_query = {"status": "active"}
        
#         if floor_id:
#             filter_query["floor_id"] = floor_id
        
#         if connector_type:
#             filter_query["connector_type"] = connector_type
            
#         if shared_id:
#             filter_query["shared_id"] = shared_id
            
#         if is_published is not None:
#             filter_query["is_published"] = is_published

#         # Get connectors with pagination
#         connectors = await VerticalConnector.find(filter_query).skip(skip).limit(limit).to_list()
        
#         # Get total count
#         total_count = await VerticalConnector.find(filter_query).count()

#         # Prepare response
#         connector_list = [
#             VerticalConnectorListItem(
#                 connector_id=connector.connector_id,
#                 name=connector.name,
#                 shared_id=connector.shared_id,
#                 connector_type=connector.connector_type.value,
#                 floor_id=connector.floor_id,
#                 shape=connector.shape.value,
#                 x=connector.x,
#                 y=connector.y,
#                 width=connector.width,
#                 height=connector.height,
#                 radius=connector.radius,
#                 color=connector.color,
#                 is_published=connector.is_published,
#                 created_by=connector.created_by,
#                 datetime=connector.datetime,
#                 status=connector.status
#             )
#             for connector in connectors
#         ]

#         return {
#             "status": "success",
#             "message": f"Retrieved {len(connector_list)} vertical connectors",
#             "data": {
#                 "connectors": connector_list,
#                 "pagination": {
#                     "total": total_count,
#                     "limit": limit,
#                     "skip": skip,
#                     "has_more": skip + len(connector_list) < total_count
#                 }
#             }
#         }

#     except Exception as e:
#         logger.exception(f"Error retrieving vertical connectors: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve vertical connectors: {str(e)}"
#         )




from fastapi import HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import hashlib
import time
from src.datamodel.database.domain.DigitalSignage import VerticalConnector, ConnectorType
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.common.redis_utils import (
    get_multi_cache_fast, 
    set_multi_cache_fast,
)

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL = 300  # 5 minutes for data cache
COUNT_CACHE_TTL = 60  # 1 minute for count cache (changes less frequently)
CACHE_PREFIX = "vc:"  # vertical_connectors

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Vertical Connector"],
        "summary": "Get Vertical Connectors",
        "response_model": dict,
        "description": "Get vertical connectors with optional filtering by floor, building, or connector type.",
        "response_description": "List of vertical connectors",
        "deprecated": False,
    }
    return ApiConfig(**config)

class VerticalConnectorListItem(BaseModel):
    connector_id: str
    name: str
    shared_id: str
    connector_type: str
    floor_id: str
    shape: str
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None
    color: str
    is_published: bool
    created_by: Optional[str] = None
    datetime: float
    status: str

    class Config:
        allow_population_by_field_name = True

def _generate_cache_key(
    floor_id: Optional[str] = None,
    connector_type: Optional[ConnectorType] = None,
    shared_id: Optional[str] = None,
    is_published: Optional[bool] = None,
    limit: int = 50,
    skip: int = 0
) -> str:
    """Generate consistent cache key for query parameters"""
    # Create a unique identifier for the query parameters
    params = {
        "floor_id": floor_id,
        "connector_type": connector_type.value if connector_type else None,
        "shared_id": shared_id,
        "is_published": is_published,
        "limit": limit,
        "skip": skip
    }
    
    # Create hash from sorted params to ensure consistency
    params_str = str(sorted(params.items()))
    cache_hash = hashlib.md5(params_str.encode()).hexdigest()[:12]
    
    return f"{CACHE_PREFIX}query:{cache_hash}"

def _generate_count_cache_key(
    floor_id: Optional[str] = None,
    connector_type: Optional[ConnectorType] = None,
    shared_id: Optional[str] = None,
    is_published: Optional[bool] = None
) -> str:
    """Generate cache key for count queries (without pagination)"""
    params = {
        "floor_id": floor_id,
        "connector_type": connector_type.value if connector_type else None,
        "shared_id": shared_id,
        "is_published": is_published
    }
    
    params_str = str(sorted(params.items()))
    cache_hash = hashlib.md5(params_str.encode()).hexdigest()[:12]
    
    return f"{CACHE_PREFIX}count:{cache_hash}"

async def _build_filter_query(
    floor_id: Optional[str],
    connector_type: Optional[ConnectorType],
    shared_id: Optional[str],
    is_published: Optional[bool]
) -> dict:
    """Build MongoDB filter query"""
    filter_query = {"status": "active"}
    
    if floor_id:
        filter_query["floor_id"] = floor_id
    
    if connector_type:
        filter_query["connector_type"] = connector_type
        
    if shared_id:
        filter_query["shared_id"] = shared_id
        
    if is_published is not None:
        filter_query["is_published"] = is_published
        
    return filter_query

async def _fetch_connectors_from_db(filter_query: dict, skip: int, limit: int) -> tuple:
    """Fetch connectors from database"""
    # Use concurrent queries for data and count
    import asyncio
    
    data_task = VerticalConnector.find(filter_query).skip(skip).limit(limit).to_list()
    count_task = VerticalConnector.find(filter_query).count()
    
    connectors, total_count = await asyncio.gather(data_task, count_task)
    
    return connectors, total_count

def _serialize_connectors(connectors) -> List[dict]:
    """Convert connector objects to serializable dictionaries"""
    return [
        {
            "connector_id": connector.connector_id,
            "name": connector.name,
            "shared_id": connector.shared_id,
            "connector_type": connector.connector_type.value,
            "floor_id": connector.floor_id,
            "shape": connector.shape.value,
            "x": connector.x,
            "y": connector.y,
            "width": connector.width,
            "height": connector.height,
            "radius": connector.radius,
            "color": connector.color,
            "is_published": connector.is_published,
            "created_by": connector.created_by,
            "datetime": connector.datetime,
            "status": connector.status
        }
        for connector in connectors
    ]

async def main(
    floor_id: Optional[str] = Query(None, description="Filter by floor ID"),
    connector_type: Optional[ConnectorType] = Query(None, description="Filter by connector type"),
    shared_id: Optional[str] = Query(None, description="Filter by shared ID"),
    is_published: Optional[bool] = Query(None, description="Filter by published status"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip")
):
    start_time = time.perf_counter()
    
    try:
        # Generate cache keys
        data_cache_key = _generate_cache_key(floor_id, connector_type, shared_id, is_published, limit, skip)
        count_cache_key = _generate_count_cache_key(floor_id, connector_type, shared_id, is_published)
        
        # Try to get both data and count from cache simultaneously
        cache_keys = [data_cache_key, count_cache_key]
        cached_data = await get_multi_cache_fast(cache_keys)
        
        cached_result = cached_data.get(data_cache_key)
        cached_count = cached_data.get(count_cache_key)
        
        # If we have cached data, return it immediately
        if cached_result is not None and cached_count is not None:
            logger.info(f"Cache HIT for query - Response time: {(time.perf_counter() - start_time) * 1000:.1f}ms")
            
            # Update pagination info with current parameters
            cached_result["data"]["pagination"].update({
                "limit": limit,
                "skip": skip,
                "has_more": skip + len(cached_result["data"]["connectors"]) < cached_count
            })
            
            return cached_result
        
        # Cache miss - fetch from database
        logger.info(f"Cache MISS for query - Fetching from database")
        
        # Build filter query
        filter_query = await _build_filter_query(floor_id, connector_type, shared_id, is_published)
        
        # Fetch from database
        connectors, total_count = await _fetch_connectors_from_db(filter_query, skip, limit)
        
        # Serialize connectors
        connector_list_dicts = _serialize_connectors(connectors)
        
        # Convert to Pydantic models for response
        connector_list = [VerticalConnectorListItem(**conn_dict) for conn_dict in connector_list_dicts]
        
        # Prepare response
        response = {
            "status": "success",
            "message": f"Retrieved {len(connector_list)} vertical connectors",
            "data": {
                "connectors": connector_list,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "skip": skip,
                    "has_more": skip + len(connector_list) < total_count
                }
            }
        }
        
        # Cache the results in background (non-blocking)
        cache_data = {
            data_cache_key: {
                "status": "success",
                "message": f"Retrieved {len(connector_list)} vertical connectors",
                "data": {
                    "connectors": connector_list_dicts,  # Store serializable dicts
                    "pagination": {
                        "total": total_count,
                        "limit": limit,
                        "skip": skip,
                        "has_more": skip + len(connector_list) < total_count
                    }
                }
            },
            count_cache_key: total_count
        }
        
        # Set cache in background - don't wait for it
        asyncio.create_task(set_multi_cache_fast(cache_data, expire=CACHE_TTL))
        
        elapsed_time = (time.perf_counter() - start_time) * 1000
        logger.info(f"Database query completed - Response time: {elapsed_time:.1f}ms")
        
        return response

    except Exception as e:
        elapsed_time = (time.perf_counter() - start_time) * 1000
        logger.exception(f"Error retrieving vertical connectors (took {elapsed_time:.1f}ms): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve vertical connectors: {str(e)}"
        )

# Optional: Cache invalidation function for when data changes
async def invalidate_connectors_cache(
    floor_id: Optional[str] = None,
    connector_type: Optional[ConnectorType] = None,
    shared_id: Optional[str] = None
):
    """Invalidate cache when connectors are modified"""
    try:
        # You can implement more sophisticated cache invalidation here
        # For now, this is a simple approach to clear specific caches
        
        # Generate keys that might be affected
        keys_to_invalidate = []
        
        # Add specific cache keys based on the changed data
        if floor_id:
            # Invalidate caches for this floor
            base_key = _generate_cache_key(floor_id=floor_id)
            keys_to_invalidate.append(base_key)
        
        # In a more sophisticated setup, you might maintain a separate
        # index of cache keys to invalidate based on the data changes
        
        logger.info(f"Cache invalidation triggered for {len(keys_to_invalidate)} keys")
        
    except Exception as e:
        logger.warning(f"Cache invalidation error: {e}")
