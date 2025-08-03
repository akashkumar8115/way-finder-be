from fastapi import HTTPException, Path, Query, status
from pydantic import BaseModel
from typing import Optional
import time
import logging
from src.datamodel.database.domain.DigitalSignage import Location, Floor
from src.datamodel.datavalidation.apiconfig import ApiConfig


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Location"],
        "summary": "Delete Location",
        "response_model": dict,
        "description": "Delete a location by ID. Can perform soft delete (default) or hard delete. Updates associated floor when hard deleting.",
        "response_description": "Deletion confirmation",
        "deprecated": False,
    }
    return ApiConfig(**config)


class DeleteResponse(BaseModel):
    deleted_id: str
    delete_type: str
    floor_updated: bool
    floor_id: Optional[str] = None
    message: str


async def main(
    location_id: str = Path(..., description="Location ID to delete"),
    hard_delete: Optional[bool] = Query(False, description="Perform hard delete (true) or soft delete (false)")
):
    try:
        # Find location by ID
        location = await Location.find_one({
            "location_id": location_id
        })
        
        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location with ID '{location_id}' not found"
            )

        floor_updated = False
        floor_id = location.floor_id

        # Update floor's locations list if location is being hard deleted
        if hard_delete and floor_id:
            # Find floor that contains this location
            floor = await Floor.find_one({
                "floor_id": floor_id,
                "locations": location_id,
                "status": "active"
            })
            
            if floor:
                # Remove location from floor's locations list
                if location_id in floor.locations:
                    floor.locations.remove(location_id)
                    floor.updated_by = None  # Set to current user if available
                    floor.update_on = time.time()
                    await floor.save()
                    floor_updated = True
                    logger.info(f"Removed location {location_id} from floor {floor_id}")

        # Delete or soft delete location
        if hard_delete:
            await location.delete()
            delete_type = "hard"
            logger.info(f"Location hard deleted: {location_id} from floor: {floor_id}")
        else:
            location.status = "deleted"
            location.updated_by = None  # Set to current user if available
            location.update_on = time.time()
            await location.save()
            delete_type = "soft"
            logger.info(f"Location soft deleted: {location_id} from floor: {floor_id}")

        response = DeleteResponse(
            deleted_id=location_id,
            delete_type=delete_type,
            floor_updated=floor_updated,
            floor_id=floor_id,
            message=f"Location {delete_type} deleted successfully"
        )

        return {
            "status": "success",
            "message": f"Location {delete_type} deleted successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting location: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete location: {str(e)}"
        )
