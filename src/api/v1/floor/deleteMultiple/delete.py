from fastapi import HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional
import time
import logging
from src.datamodel.database.domain.DigitalSignage import Floor, Location, Building
from src.datamodel.datavalidation.apiconfig import ApiConfig


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Floor"],
        "summary": "Bulk Delete Floors",
        "response_model": dict,
        "description": "Delete multiple floors by their IDs.",
        "response_description": "Bulk deletion confirmation",
        "deprecated": False,
    }
    return ApiConfig(**config)


class BulkDeleteRequest(BaseModel):
    floor_ids: List[str] = Field(..., description="List of floor IDs to delete")


class BulkDeleteResponse(BaseModel):
    deleted_floors: List[str]
    failed_deletions: List[str]
    delete_type: str
    total_affected_locations: int
    buildings_updated: List[str]
    message: str


async def main(
    delete_data: BulkDeleteRequest,
    hard_delete: Optional[bool] = Query(False, description="Perform hard delete (true) or soft delete (false)"),
    cascade: Optional[bool] = Query(True, description="Also delete associated locations")
):
    try:
        if not delete_data.floor_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No floor IDs provided for deletion"
            )

        deleted_floors = []
        failed_deletions = []
        total_affected_locations = 0
        buildings_updated = []

        for floor_id in delete_data.floor_ids:
            try:
                # Find floor by ID
                floor = await Floor.find_one({
                    "floor_id": floor_id
                })
                
                if not floor:
                    failed_deletions.append(floor_id)
                    logger.warning(f"Floor not found: {floor_id}")
                    continue

                affected_locations = 0

                # Handle cascade deletion of locations
                if cascade and floor.locations:
                    locations = await Location.find({
                        "location_id": {"$in": floor.locations},
                        "status": "active"
                    }).to_list()
                    
                    affected_locations = len(locations)
                    
                    # Delete locations
                    for location in locations:
                        if hard_delete:
                            await location.delete()
                        else:
                            location.status = "deleted"
                            location.updated_by = None  # Set to current user if available
                            location.update_on = time.time()
                            await location.save()

                # Update building's floors list if floor is being hard deleted
                if hard_delete and floor.building_id:
                    building = await Building.find_one({
                        "building_id": floor.building_id
                    })
                    
                    if building and floor.floor_id in building.floors:
                        building.floors.remove(floor.floor_id)
                        building.updated_by = None  # Set to current user if available
                        building.update_on = time.time()
                        await building.save()
                        
                        if floor.building_id not in buildings_updated:
                            buildings_updated.append(floor.building_id)

                # Delete floor
                if hard_delete:
                    await floor.delete()
                else:
                    floor.status = "deleted"
                    floor.updated_by = None  # Set to current user if available
                    floor.update_on = time.time()
                    await floor.save()

                deleted_floors.append(floor_id)
                total_affected_locations += affected_locations

                logger.info(f"Successfully deleted floor: {floor_id}")

            except Exception as e:
                logger.error(f"Failed to delete floor {floor_id}: {str(e)}")
                failed_deletions.append(floor_id)

        delete_type = "hard" if hard_delete else "soft"
        
        logger.info(f"Bulk {delete_type} delete completed. Success: {len(deleted_floors)}, Failed: {len(failed_deletions)}")

        response = BulkDeleteResponse(
            deleted_floors=deleted_floors,
            failed_deletions=failed_deletions,
            delete_type=delete_type,
            total_affected_locations=total_affected_locations,
            buildings_updated=buildings_updated,
            message=f"Bulk {delete_type} delete completed. Deleted: {len(deleted_floors)}, Failed: {len(failed_deletions)}"
        )

        # Determine response status based on results
        if len(deleted_floors) == len(delete_data.floor_ids):
            status_message = "All floors deleted successfully"
        elif len(deleted_floors) > 0:
            status_message = "Partial deletion completed"
        else:
            status_message = "No floors were deleted"

        return {
            "status": "success" if len(deleted_floors) > 0 else "warning",
            "message": status_message,
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in bulk delete floors: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform bulk delete: {str(e)}"
        )
