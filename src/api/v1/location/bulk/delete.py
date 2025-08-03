from fastapi import HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional
import time
import logging
from src.datamodel.database.domain.DigitalSignage import Location
from src.datamodel.datavalidation.apiconfig import ApiConfig


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Location"],
        "summary": "Bulk Delete Locations",
        "response_model": dict,
        "description": "Delete multiple locations by their IDs.",
        "response_description": "Bulk deletion confirmation",
        "deprecated": False,
    }
    return ApiConfig(**config)


class BulkDeleteRequest(BaseModel):
    location_ids: List[str] = Field(..., description="List of location IDs to delete")


class LocationDeleteInfo(BaseModel):
    location_id: str
    name: str
    floor_id: str
    category: str


class BulkDeleteResponse(BaseModel):
    deleted_locations: List[LocationDeleteInfo]
    failed_deletions: List[str]
    delete_type: str
    floors_affected: List[str]
    message: str


async def main(
    delete_data: BulkDeleteRequest,
    hard_delete: Optional[bool] = Query(False, description="Perform hard delete (true) or soft delete (false)")
):
    try:
        if not delete_data.location_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No location IDs provided for deletion"
            )

        deleted_locations = []
        failed_deletions = []
        floors_affected = set()

        for location_id in delete_data.location_ids:
            try:
                # Find location by ID
                location = await Location.find_one({
                    "location_id": location_id
                })
                
                if not location:
                    failed_deletions.append(location_id)
                    logger.warning(f"Location not found: {location_id}")
                    continue

                # Track affected floors
                if location.floor_id:
                    floors_affected.add(location.floor_id)

                # Delete location
                if hard_delete:
                    await location.delete()
                else:
                    location.status = "deleted"
                    location.updated_by = None  # Set to current user if available
                    location.update_on = time.time()
                    await location.save()

                # Add to successful deletions with detailed info
                deleted_location_info = LocationDeleteInfo(
                    location_id=location.location_id,
                    name=location.name,
                    floor_id=location.floor_id,
                    category=location.category
                )
                deleted_locations.append(deleted_location_info)
                
                logger.info(f"Successfully {'hard' if hard_delete else 'soft'} deleted location: {location_id} on floor: {location.floor_id}")

            except Exception as e:
                logger.error(f"Failed to delete location {location_id}: {str(e)}")
                failed_deletions.append(location_id)

        delete_type = "hard" if hard_delete else "soft"
        
        logger.info(f"Bulk {delete_type} delete completed. Success: {len(deleted_locations)}, Failed: {len(failed_deletions)}, Floors affected: {len(floors_affected)}")

        response = BulkDeleteResponse(
            deleted_locations=deleted_locations,
            failed_deletions=failed_deletions,
            delete_type=delete_type,
            floors_affected=list(floors_affected),
            message=f"Bulk {delete_type} delete completed. Deleted: {len(deleted_locations)}, Failed: {len(failed_deletions)}, Floors affected: {len(floors_affected)}"
        )

        # Determine response status based on results
        if len(deleted_locations) == len(delete_data.location_ids):
            status_message = "All locations deleted successfully"
        elif len(deleted_locations) > 0:
            status_message = "Partial deletion completed"
        else:
            status_message = "No locations were deleted"

        return {
            "status": "success" if len(deleted_locations) > 0 else "warning",
            "message": status_message,
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in bulk delete locations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform bulk delete: {str(e)}"
        )
