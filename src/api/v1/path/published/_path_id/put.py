from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
import time
import logging
from src.datamodel.database.domain.DigitalSignage import Path, Floor, Building
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Path"],
        "summary": "Toggle Path Publish Status",
        "response_model": dict,
        "description": "Toggle the publish status of a path. If published, it will be unpublished and vice versa. Supports both single-floor and multi-floor paths.",
        "response_description": "Updated path publish status",
        "deprecated": False,
    }
    return ApiConfig(**config)


class PathTogglePublishResponse(BaseModel):
    path_id: str
    name: str
    is_multi_floor: bool
    building_id: Optional[str] = None
    floor_id: Optional[str] = None
    source: str
    destination: str
    is_published: bool
    update_on: float
    status: str
    previous_publish_status: bool

    class Config:
        allow_population_by_field_name = True

async def main(path_id: str):
    """
    Main function to toggle path publish status
    
    Args:
        path_id: Path ID from URL parameter
        toggle_data: Request body with optional updated_by field
    """
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

        # Store the previous publish status for response
        previous_publish_status = path.is_published
        
        # Toggle the publish status
        new_publish_status = not path.is_published
        
        # Update the path
        path.is_published = new_publish_status
        path.update_on = time.time()
        
        # Save the updated path
        await path.save()
        
        # Log the action
        action = "published" if new_publish_status else "unpublished"
        logger.info(f"Path {path.path_id} has been {action}")
        
        # Prepare response
        response = PathTogglePublishResponse(
            path_id=path.path_id,
            name=path.name,
            is_multi_floor=path.is_multi_floor,
            building_id=path.building_id,
            floor_id=path.floor_id,
            source=path.source,
            destination=path.destination,
            is_published=path.is_published,
            update_on=path.update_on,
            status=path.status,
            previous_publish_status=previous_publish_status
        )
        
        success_message = f"Path '{path.name}' has been {'published' if new_publish_status else 'unpublished'} successfully"
        
        return {
            "status": "success",
            "message": success_message,
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error toggling path publish status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle path publish status: {str(e)}"
        )