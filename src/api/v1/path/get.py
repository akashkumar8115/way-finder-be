# from fastapi import HTTPException, Query, status
# from pydantic import BaseModel, Field
# from typing import Optional, List
# import logging
# from src.datamodel.database.domain.DigitalSignage import Path
# from src.datamodel.datavalidation.apiconfig import ApiConfig

# logger = logging.getLogger(__name__)

# def api_config():
#     config = {
#         "path": "",
#         "status_code": 200,
#         "tags": ["Path"],
#         "summary": "Get Paths",
#         "response_model": dict,
#         "description": "Get navigation paths with optional filtering by floor, source, or destination.",
#         "response_description": "List of paths",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)

# class PathListItem(BaseModel):
#     path_id: str
#     name: str
#     floor_id: str
#     source: str
#     destination: str
#     source_tag_id: Optional[str] = None
#     destination_tag_id: Optional[str] = None
#     points: List[dict]
#     shape: str
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
#     source_tag_id: Optional[str] = Query(None, description="Filter by source location/connector ID"),
#     destination_tag_id: Optional[str] = Query(None, description="Filter by destination location/connector ID"),
#     is_published: Optional[bool] = Query(None, description="Filter by published status"),
#     limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
#     skip: int = Query(0, ge=0, description="Number of results to skip")
# ):
#     try:
#         # Build filter query
#         filter_query = {"status": "active"}
        
#         if floor_id:
#             filter_query["floor_id"] = floor_id
        
#         if source_tag_id:
#             filter_query["source_tag_id"] = source_tag_id
            
#         if destination_tag_id:
#             filter_query["destination_tag_id"] = destination_tag_id
            
#         if is_published is not None:
#             filter_query["is_published"] = is_published

#         # Get paths with pagination
#         paths = await Path.find(filter_query).skip(skip).limit(limit).to_list()
        
#         # Get total count
#         total_count = await Path.find(filter_query).count()

#         # Prepare response
#         path_list = [
#             PathListItem(
#                 path_id=path.path_id,
#                 name=path.name,
#                 floor_id=path.floor_id,
#                 source=path.source,
#                 destination=path.destination,
#                 source_tag_id=path.source_tag_id,
#                 destination_tag_id=path.destination_tag_id,
#                 points=[{"x": point.x, "y": point.y} for point in path.points],
#                 shape=path.shape.value,
#                 width=path.width,
#                 height=path.height,
#                 radius=path.radius,
#                 color=path.color,
#                 is_published=path.is_published,
#                 created_by=path.created_by,
#                 datetime=path.datetime,
#                 status=path.status
#             )
#             for path in paths
#         ]

#         return {
#             "status": "success",
#             "message": f"Retrieved {len(path_list)} paths",
#             "data": {
#                 "paths": path_list,
#                 "pagination": {
#                     "total": total_count,
#                     "limit": limit,
#                     "skip": skip,
#                     "has_more": skip + len(path_list) < total_count
#                 }
#             }
#         }

#     except Exception as e:
#         logger.exception(f"Error retrieving paths: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve paths: {str(e)}"
#         )



from fastapi import HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from src.datamodel.database.domain.DigitalSignage import Path
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Path"],
        "summary": "Get Paths (Single or Multi-Floor)",
        "response_model": dict,
        "description": "Get navigation paths with optional filtering. Supports both single-floor and multi-floor paths.",
        "response_description": "List of paths with pagination",
        "deprecated": False,
    }
    return ApiConfig(**config)

class PathListItem(BaseModel):
    path_id: str
    name: str
    is_multi_floor: bool
    
    # Single-floor fields
    floor_id: Optional[str] = None
    points: Optional[List[dict]] = None
    
    # Multi-floor fields
    building_id: Optional[str] = None
    source_floor_id: Optional[str] = None
    destination_floor_id: Optional[str] = None
    floor_segments: Optional[List[dict]] = None
    vertical_transitions: Optional[List[dict]] = None
    total_floors: Optional[int] = None
    
    # Common fields
    source: str
    destination: str
    source_tag_id: Optional[str] = None
    destination_tag_id: Optional[str] = None
    shape: str
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None
    color: str
    is_published: bool
    created_by: Optional[str] = None
    datetime: float
    status: str
    estimated_time: Optional[int] = None
    metadata: Optional[dict] = None

    class Config:
        allow_population_by_field_name = True

async def main(
    # Single-floor filters
    floor_id: Optional[str] = Query(None, description="Filter by floor ID (single-floor paths)"),
    
    # Multi-floor filters
    building_id: Optional[str] = Query(None, description="Filter by building ID (multi-floor paths)"),
    source_floor_id: Optional[str] = Query(None, description="Filter by source floor ID (multi-floor paths)"),
    destination_floor_id: Optional[str] = Query(None, description="Filter by destination floor ID (multi-floor paths)"),
    
    # Common filters
    is_multi_floor: Optional[bool] = Query(None, description="Filter by path type (True for multi-floor, False for single-floor)"),
    source_tag_id: Optional[str] = Query(None, description="Filter by source location/connector ID"),
    destination_tag_id: Optional[str] = Query(None, description="Filter by destination location/connector ID"),
    is_published: Optional[bool] = Query(None, description="Filter by published status"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    
    # Search and sorting
    search: Optional[str] = Query(None, description="Search in path names, source, or destination"),
    sort_by: Optional[str] = Query("datetime", description="Sort by field (datetime, name, source, destination)"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc, desc)"),
    
    # Pagination
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip")
):
    try:
        # Build filter query
        filter_query = {"status": "active"}
        
        # Path type filter
        if is_multi_floor is not None:
            filter_query["is_multi_floor"] = is_multi_floor
        
        # Single-floor specific filters
        if floor_id:
            filter_query["floor_id"] = floor_id
            # Ensure we're only looking at single-floor paths
            filter_query["is_multi_floor"] = False
        
        # Multi-floor specific filters
        if building_id:
            filter_query["building_id"] = building_id
            # Ensure we're only looking at multi-floor paths
            filter_query["is_multi_floor"] = True
            
        if source_floor_id:
            filter_query["source_floor_id"] = source_floor_id
            filter_query["is_multi_floor"] = True
            
        if destination_floor_id:
            filter_query["destination_floor_id"] = destination_floor_id
            filter_query["is_multi_floor"] = True
        
        # Common filters
        if source_tag_id:
            filter_query["source_tag_id"] = source_tag_id
            
        if destination_tag_id:
            filter_query["destination_tag_id"] = destination_tag_id
            
        if is_published is not None:
            filter_query["is_published"] = is_published
            
        if created_by:
            filter_query["created_by"] = created_by

        # Search functionality
        if search:
            search_filter = {
                "$or": [
                    {"name": {"$regex": search, "$options": "i"}},
                    {"source": {"$regex": search, "$options": "i"}},
                    {"destination": {"$regex": search, "$options": "i"}}
                ]
            }
            filter_query.update(search_filter)

        # Build sort criteria
        sort_field = sort_by if sort_by in ["datetime", "name", "source", "destination"] else "datetime"
        sort_direction = -1 if sort_order.lower() == "desc" else 1
        
        # Get paths with pagination and sorting
        paths_cursor = Path.find(filter_query).sort(sort_field, sort_direction).skip(skip).limit(limit)
        paths = await paths_cursor.to_list()
        
        # Get total count
        total_count = await Path.find(filter_query).count()

        # Prepare response
        path_list = []
        for path in paths:
            if path.is_multi_floor:
                # Multi-floor path response
                path_item = PathListItem(
                    path_id=path.path_id,
                    name=path.name,
                    is_multi_floor=True,
                    building_id=path.building_id,
                    source_floor_id=path.source_floor_id,
                    destination_floor_id=path.destination_floor_id,
                    source=path.source,
                    destination=path.destination,
                    source_tag_id=path.source_tag_id,
                    destination_tag_id=path.destination_tag_id,
                    floor_segments=path.floor_segments,
                    vertical_transitions=path.vertical_transitions,
                    total_floors=path.total_floors,
                    shape=path.shape.value,
                    width=path.width,
                    height=path.height,
                    radius=path.radius,
                    color=path.color,
                    is_published=path.is_published,
                    created_by=path.created_by,
                    datetime=path.datetime,
                    status=path.status,
                    estimated_time=getattr(path, 'estimated_time', None) or (path.metadata.get('estimated_time') if path.metadata else None),
                    metadata=path.metadata
                )
            else:
                # Single-floor path response
                path_item = PathListItem(
                    path_id=path.path_id,
                    name=path.name,
                    is_multi_floor=False,
                    floor_id=path.floor_id,
                    source=path.source,
                    destination=path.destination,
                    source_tag_id=path.source_tag_id,
                    destination_tag_id=path.destination_tag_id,
                    points=[{"x": point.x, "y": point.y} for point in path.points],
                    shape=path.shape.value,
                    width=path.width,
                    height=path.height,
                    radius=path.radius,
                    color=path.color,
                    is_published=path.is_published,
                    created_by=path.created_by,
                    datetime=path.datetime,
                    status=path.status,
                    estimated_time=getattr(path, 'estimated_time', None) or (path.metadata.get('estimated_time') if path.metadata else None),
                    metadata=path.metadata
                )
            
            path_list.append(path_item)

        # Prepare summary statistics
        single_floor_count = len([p for p in path_list if not p.is_multi_floor])
        multi_floor_count = len([p for p in path_list if p.is_multi_floor])

        return {
            "status": "success",
            "message": f"Retrieved {len(path_list)} paths ({single_floor_count} single-floor, {multi_floor_count} multi-floor)",
            "data": {
                "paths": path_list,
                "summary": {
                    "total_paths": len(path_list),
                    "single_floor_paths": single_floor_count,
                    "multi_floor_paths": multi_floor_count
                },
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "skip": skip,
                    "has_more": skip + len(path_list) < total_count
                },
                "filters_applied": {
                    "is_multi_floor": is_multi_floor,
                    "floor_id": floor_id,
                    "building_id": building_id,
                    "source_floor_id": source_floor_id,
                    "destination_floor_id": destination_floor_id,
                    "is_published": is_published,
                    "search": search,
                    "sort_by": sort_field,
                    "sort_order": sort_order
                }
            }
        }

    except Exception as e:
        logger.exception(f"Error retrieving paths: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve paths: {str(e)}"
        )
