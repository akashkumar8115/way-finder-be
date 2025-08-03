from fastapi import HTTPException, Path as FastAPIPath, status
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import time
import logging
from src.datamodel.database.domain.DigitalSignage import Path, PathPoint, ShapeType, Location, VerticalConnector
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Path"],
        "summary": "Update Path",
        "response_model": dict,
        "description": "Update an existing navigation path.",
        "response_description": "Updated path data",
        "deprecated": False,
    }
    return ApiConfig(**config)

class PathPointRequest(BaseModel):
    x: float = Field(..., description="X coordinate of path point")
    y: float = Field(..., description="Y coordinate of path point")

class PathUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Name of the path")
    source: Optional[str] = Field(None, description="Source location/connector name")
    destination: Optional[str] = Field(None, description="Destination location/connector name")
    source_tag_id: Optional[str] = Field(None, description="Source location/connector ID")
    destination_tag_id: Optional[str] = Field(None, description="Destination location/connector ID")
    points: Optional[List[PathPointRequest]] = Field(None, description="Array of path points", min_items=2)
    shape: Optional[ShapeType] = Field(None, description="Shape type for path visualization")
    width: Optional[float] = Field(None, description="Width for rectangle shape")
    height: Optional[float] = Field(None, description="Height for rectangle shape")
    radius: Optional[float] = Field(None, description="Radius for circle shape")
    color: Optional[str] = Field(None, description="Color for path display")
    is_published: Optional[bool] = Field(None, description="Whether path is published")
    updated_by: Optional[str] = Field(None, description="User who updated the path")

    @validator('color')
    def validate_color_format(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be in hex format (e.g., #3b82f6)')
        if v and len(v) != 7:
            raise ValueError('Color must be 7 characters long including # (e.g., #3b82f6)')
        return v

    @validator('points')
    def validate_points(cls, v):
        if v is not None and len(v) < 2:
            raise ValueError('Path must have at least 2 points')
        return v

    class Config:
        allow_population_by_field_name = True

class PathUpdateResponse(BaseModel):
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
    path_id: str = FastAPIPath(..., description="Path ID to update"),
    path_data: PathUpdateRequest = None
):
    try:
        # Find the existing path
        existing_path = await Path.find_one({
            "path_id": path_id,
            "status": "active"
        })
        
        if not existing_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path with ID '{path_id}' not found"
            )

        # Validate shape-specific requirements if shape is being updated
        if path_data.shape:
            if path_data.shape == ShapeType.RECTANGLE:
                width = path_data.width if path_data.width is not None else existing_path.width
                height = path_data.height if path_data.height is not None else existing_path.height
                if not width or not height:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Width and height are required for rectangle shape"
                    )
            elif path_data.shape == ShapeType.CIRCLE:
                radius = path_data.radius if path_data.radius is not None else existing_path.radius
                if not radius:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Radius is required for circle shape"
                    )

        # Validate source and destination IDs if provided
        if path_data.source_tag_id:
            source_exists = await _validate_tag_exists(path_data.source_tag_id, existing_path.floor_id)
            if not source_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Source location/connector with ID '{path_data.source_tag_id}' not found on this floor"
                )

        if path_data.destination_tag_id:
            dest_exists = await _validate_tag_exists(path_data.destination_tag_id, existing_path.floor_id)
            if not dest_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Destination location/connector with ID '{path_data.destination_tag_id}' not found on this floor"
                )

        # Check if updated name conflicts with existing paths
        if path_data.name and path_data.name != existing_path.name:
            name_conflict = await Path.find_one({
                "name": path_data.name,
                "floor_id": existing_path.floor_id,
                "path_id": {"$ne": path_id},
                "status": "active"
            })
            
            if name_conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Path with name '{path_data.name}' already exists on this floor"
                )

        # Update fields
        update_data = {}
        
        if path_data.name is not None:
            update_data["name"] = path_data.name
        if path_data.source is not None:
            update_data["source"] = path_data.source
        if path_data.destination is not None:
            update_data["destination"] = path_data.destination
        if path_data.source_tag_id is not None:
            update_data["source_tag_id"] = path_data.source_tag_id
        if path_data.destination_tag_id is not None:
            update_data["destination_tag_id"] = path_data.destination_tag_id
        if path_data.points is not None:
            update_data["points"] = [PathPoint(x=point.x, y=point.y) for point in path_data.points]
        if path_data.shape is not None:
            update_data["shape"] = path_data.shape
        if path_data.width is not None:
            update_data["width"] = path_data.width
        if path_data.height is not None:
            update_data["height"] = path_data.height
        if path_data.radius is not None:
            update_data["radius"] = path_data.radius
        if path_data.color is not None:
            update_data["color"] = path_data.color
        if path_data.is_published is not None:
            update_data["is_published"] = path_data.is_published
        if path_data.updated_by is not None:
            update_data["updated_by"] = path_data.updated_by
        
        update_data["update_on"] = time.time()

        # Update the path
        for key, value in update_data.items():
            setattr(existing_path, key, value)
        
        await existing_path.save()
        
        logger.info(f"Path updated successfully: {path_id}")

        # Prepare response
        response = PathUpdateResponse(
            path_id=existing_path.path_id,
            name=existing_path.name,
            floor_id=existing_path.floor_id,
            source=existing_path.source,
            destination=existing_path.destination,
            source_tag_id=existing_path.source_tag_id,
            destination_tag_id=existing_path.destination_tag_id,
            points=[{"x": point.x, "y": point.y} for point in existing_path.points],
            shape=existing_path.shape.value,
            width=existing_path.width,
            height=existing_path.height,
            radius=existing_path.radius,
            color=existing_path.color,
            is_published=existing_path.is_published,
            created_by=existing_path.created_by,
            datetime=existing_path.datetime,
            updated_by=existing_path.updated_by,
            update_on=existing_path.update_on,
            status=existing_path.status,
            metadata=existing_path.metadata
        )

        return {
            "status": "success",
            "message": "Path updated successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating path: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update path: {str(e)}"
        )

async def _validate_tag_exists(tag_id: str, floor_id: str) -> bool:
    """
    Validate if a location or vertical connector exists on the specified floor
    """
    try:
        # Check if it's a location
        location = await Location.find_one({
            "location_id": tag_id,
            "floor_id": floor_id,
            "status": "active"
        })
        
        if location:
            return True
        
        # Check if it's a vertical connector
        connector = await VerticalConnector.find_one({
            "connector_id": tag_id,
            "floor_id": floor_id,
            "status": "active"
        })
        
        return connector is not None
        
    except Exception as e:
        logger.error(f"Error validating tag existence: {str(e)}")
        return False
