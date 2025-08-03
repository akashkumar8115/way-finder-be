from fastapi import HTTPException, Path as FastAPIPath, Query, status
from typing import Optional
import time
import logging
from src.datamodel.database.domain.DigitalSignage import Path, Floor
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Path"],
        "summary": "Delete Path",
        "response_model": dict,
        "description": "Delete a navigation path by marking it as inactive.",
        "response_description": "Deletion confirmation",
        "deprecated": False,
    }
    return ApiConfig(**config)

async def main(
    path_id: str = FastAPIPath(..., description="Path ID to delete"),
    deleted_by: Optional[str] = Query(None, description="User who deleted the path")
):
    try:
        # Find the path
        existing_path = await Path.find_one({
            "path_id": path_id,
            "status": "active"
        })
        
        if not existing_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path with ID '{path_id}' not found"
            )

        # Mark path as inactive (soft delete)
        existing_path.status = "inactive"
        existing_path.updated_by = deleted_by
        existing_path.update_on = time.time()
        
        await existing_path.save()
        
        # Remove path from floor's paths list
        try:
            floor = await Floor.find_one({
                "floor_id": existing_path.floor_id,
                "status": "active"
            })
            
            if floor and path_id in floor.paths:
                floor.paths.remove(path_id)
                floor.updated_by = deleted_by
                floor.update_on = time.time()
                await floor.save()
                logger.info(f"Removed path {path_id} from floor {existing_path.floor_id}")
        
        except Exception as floor_update_error:
            logger.warning(f"Failed to update floor paths list: {str(floor_update_error)}")
            # Don't fail the deletion if floor update fails
        
        logger.info(f"Path deleted successfully: {path_id}")

        return {
            "status": "success",
            "message": "Path deleted successfully",
            "data": {
                "path_id": path_id,
                "name": existing_path.name,
                "floor_id": existing_path.floor_id,
                "deleted_at": existing_path.update_on,
                "deleted_by": deleted_by
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting path: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete path: {str(e)}"
        )
