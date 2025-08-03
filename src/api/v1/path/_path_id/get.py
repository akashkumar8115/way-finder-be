# from fastapi import HTTPException, Path as FastAPIPath, status
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
#         "summary": "Get Path by ID",
#         "response_model": dict,
#         "description": "Get a specific navigation path by its ID.",
#         "response_description": "Path details",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)

# class PathDetailResponse(BaseModel):
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
#     updated_by: Optional[str] = None
#     update_on: Optional[float] = None
#     status: str
#     metadata: Optional[dict] = None

#     class Config:
#         allow_population_by_field_name = True

# async def main(
#     path_id: str = FastAPIPath(..., description="Path ID to retrieve")
# ):
#     try:
#         # Find the path by ID
#         path = await Path.find_one({
#             "path_id": path_id,
#             "status": "active"
#         })
        
#         if not path:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Path with ID '{path_id}' not found"
#             )

#         # Prepare response
#         response = PathDetailResponse(
#             path_id=path.path_id,
#             name=path.name,
#             floor_id=path.floor_id,
#             source=path.source,
#             destination=path.destination,
#             source_tag_id=path.source_tag_id,
#             destination_tag_id=path.destination_tag_id,
#             points=[{"x": point.x, "y": point.y} for point in path.points],
#             shape=path.shape.value,
#             width=path.width,
#             height=path.height,
#             radius=path.radius,
#             color=path.color,
#             is_published=path.is_published,
#             created_by=path.created_by,
#             datetime=path.datetime,
#             updated_by=path.updated_by,
#             update_on=path.update_on,
#             status=path.status,
#             metadata=path.metadata
#         )

#         return {
#             "status": "success",
#             "message": "Path retrieved successfully",
#             "data": response
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception(f"Error retrieving path: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve path: {str(e)}"
#         )



from fastapi import HTTPException, Path as FastAPIPath, status
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
        "summary": "Get Path by ID (Single or Multi-Floor)",
        "response_model": dict,
        "description": "Get a specific navigation path by its ID. Supports both single-floor and multi-floor paths.",
        "response_description": "Path details",
        "deprecated": False,
    }
    return ApiConfig(**config)

class PathDetailResponse(BaseModel):
    path_id: str
    name: str
    is_multi_floor: bool
    building_id: Optional[str] = None
    floor_id: Optional[str] = None
    source: str
    destination: str
    source_tag_id: Optional[str] = None
    destination_tag_id: Optional[str] = None
    
    # Single-floor fields
    points: Optional[List[dict]] = None
    
    # Multi-floor fields
    floor_segments: Optional[List[dict]] = None
    vertical_transitions: Optional[List[dict]] = None
    total_floors: Optional[int] = None
    source_floor_id: Optional[str] = None
    destination_floor_id: Optional[str] = None
    
    # Common fields
    shape: str
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None
    color: str
    is_published: bool
    created_by: Optional[str] = None
    datetime: float
    updated_by: Optional[str] = None
    update_on: Optional[float] = None
    status: str
    estimated_time: Optional[int] = None
    metadata: Optional[dict] = None

    class Config:
        allow_population_by_field_name = True

async def main(
    path_id: str = FastAPIPath(..., description="Path ID to retrieve")
):
    try:
        # Find the path by ID
        path = await Path.find_one({
            "path_id": path_id,
            "status": "active"
        })
        
        if not path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path with ID '{path_id}' not found"
            )

        # Extract estimated_time from metadata if it exists
        estimated_time = None
        if hasattr(path, 'metadata') and path.metadata:
            estimated_time = path.metadata.get('estimated_time')

        # Prepare response based on path type
        if getattr(path, 'is_multi_floor', False):
            # Multi-floor path response
            response = PathDetailResponse(
                path_id=path.path_id,
                name=path.name,
                is_multi_floor=True,
                building_id=getattr(path, 'building_id', None),
                source_floor_id=getattr(path, 'source_floor_id', None),
                destination_floor_id=getattr(path, 'destination_floor_id', None),
                source=path.source,
                destination=path.destination,
                source_tag_id=path.source_tag_id,
                destination_tag_id=path.destination_tag_id,
                floor_segments=getattr(path, 'floor_segments', []),
                vertical_transitions=getattr(path, 'vertical_transitions', []),
                total_floors=getattr(path, 'total_floors', 0),
                shape=path.shape.value,
                width=path.width,
                height=path.height,
                radius=path.radius,
                color=path.color,
                is_published=path.is_published,
                created_by=path.created_by,
                datetime=path.datetime,
                updated_by=path.updated_by,
                update_on=path.update_on,
                status=path.status,
                estimated_time=estimated_time,
                metadata=path.metadata
            )
            
            message = "Multi-floor path retrieved successfully"
            
        else:
            # Single-floor path response
            response = PathDetailResponse(
                path_id=path.path_id,
                name=path.name,
                is_multi_floor=False,
                floor_id=path.floor_id,
                source=path.source,
                destination=path.destination,
                source_tag_id=path.source_tag_id,
                destination_tag_id=path.destination_tag_id,
                points=[{"x": point.x, "y": point.y} for point in path.points] if path.points else [],
                shape=path.shape.value,
                width=path.width,
                height=path.height,
                radius=path.radius,
                color=path.color,
                is_published=path.is_published,
                created_by=path.created_by,
                datetime=path.datetime,
                updated_by=path.updated_by,
                update_on=path.update_on,
                status=path.status,
                estimated_time=estimated_time,
                metadata=path.metadata
            )
            
            message = "Single-floor path retrieved successfully"

        return {
            "status": "success",
            "message": message,
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving path: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve path: {str(e)}"
        )
