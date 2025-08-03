from fastapi import HTTPException, Query, Path, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from src.datamodel.database.domain.DigitalSignage import Path as PathModel, Floor
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Path"],
        "summary": "Get Paths by Floor ID",
        "response_model": dict,
        "description": "Retrieve all navigation paths for a specific floor.",
        "response_description": "List of paths for the specified floor",
        "deprecated": False,
    }
    return ApiConfig(**config)

class PathResponse(BaseModel):
    path_id: str
    name: str
    floor_id: str
    source: str
    destination: str
    source_tag_id: Optional[str] = None
    destination_tag_id: Optional[str] = None
    points: List[dict]
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
    metadata: Optional[dict] = None

    class Config:
        allow_population_by_field_name = True

async def main(
    floor_id: str = Path(..., description="ID of the floor to get paths for"),
    is_published: Optional[bool] = Query(None, description="Filter by published status"),
    status_filter: str = Query("active", description="Filter by path status")
):
    try:
        # Check if floor exists
        floor = await Floor.find_one({
            "floor_id": floor_id,
            "status": "active"
        })
        
        if not floor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Floor with ID '{floor_id}' not found"
            )

        # Build query filter
        query_filter = {
            "floor_id": floor_id,
            "status": status_filter
        }
        
        # Add published filter if specified
        if is_published is not None:
            query_filter["is_published"] = is_published

        # Get all paths for the floor
        paths = await PathModel.find(query_filter).to_list()
        
        if not paths:
            return {
                "status": "success",
                "message": f"No paths found for floor '{floor_id}'",
                "data": {
                    "floor_id": floor_id,
                    "paths": [],
                    "total_count": 0
                }
            }

        # Convert paths to response format
        path_responses = []
        for path in paths:
            path_response = PathResponse(
                path_id=path.path_id,
                name=path.name,
                floor_id=path.floor_id,
                source=path.source,
                destination=path.destination,
                source_tag_id=path.source_tag_id,
                destination_tag_id=path.destination_tag_id,
                points=[{"x": point.x, "y": point.y} for point in path.points],
                shape=path.shape.value if hasattr(path.shape, 'value') else str(path.shape),
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
                metadata=path.metadata
            )
            path_responses.append(path_response)

        logger.info(f"Retrieved {len(path_responses)} paths for floor: {floor_id}")

        return {
            "status": "success",
            "message": f"Successfully retrieved paths for floor '{floor_id}'",
            "data": {
                "floor_id": floor_id,
                "paths": [path.dict() for path in path_responses],
                "total_count": len(path_responses)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving paths for floor {floor_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve paths: {str(e)}"
        )
