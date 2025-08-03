from fastapi import HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional
import time
import logging
from src.datamodel.database.domain.DigitalSignage import Building, Floor, Location
from src.datamodel.datavalidation.apiconfig import ApiConfig


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Building"],
        "summary": "Bulk Delete Buildings",
        "response_model": dict,
        "description": "Delete multiple buildings by their IDs.",
        "response_description": "Bulk deletion confirmation",
        "deprecated": False,
    }
    return ApiConfig(**config)


class BulkDeleteRequest(BaseModel):
    building_ids: List[str] = Field(..., description="List of building IDs to delete")


class BulkDeleteResponse(BaseModel):
    deleted_buildings: List[str]
    failed_deletions: List[str]
    delete_type: str
    total_affected_floors: int
    total_affected_locations: int
    message: str


async def main(
    delete_data: BulkDeleteRequest,
    hard_delete: Optional[bool] = Query(False, description="Perform hard delete (true) or soft delete (false)"),
    cascade: Optional[bool] = Query(True, description="Also delete associated floors and locations")
):
    try:
        if not delete_data.building_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No building IDs provided for deletion"
            )

        deleted_buildings = []
        failed_deletions = []
        total_affected_floors = 0
        total_affected_locations = 0

        for building_id in delete_data.building_ids:
            try:
                # Find building by ID
                building = await Building.find_one({
                    "building_id": building_id
                })
                
                if not building:
                    failed_deletions.append(building_id)
                    logger.warning(f"Building not found: {building_id}")
                    continue

                affected_floors = 0
                affected_locations = 0

                # Handle cascade deletion
                if cascade and building.floors:
                    floors = await Floor.find({
                        "building_id": building_id,
                        "status": "active"
                    }).to_list()
                    
                    affected_floors = len(floors)
                    
                    for floor in floors:
                        if floor.locations:
                            locations = await Location.find({
                                "location_id": {"$in": floor.locations},
                                "status": "active"
                            }).to_list()
                            
                            affected_locations += len(locations)
                            
                            # Delete locations
                            for location in locations:
                                if hard_delete:
                                    await location.delete()
                                else:
                                    location.status = "deleted"
                                    location.updated_by = None  # Set to current user if available
                                    location.update_on = time.time()
                                    await location.save()
                        
                        # Delete floor
                        if hard_delete:
                            await floor.delete()
                        else:
                            floor.status = "deleted"
                            floor.updated_by = None  # Set to current user if available
                            floor.update_on = time.time()
                            await floor.save()

                # Delete building
                if hard_delete:
                    await building.delete()
                else:
                    building.status = "deleted"
                    building.updated_by = None  # Set to current user if available
                    building.update_on = time.time()
                    await building.save()

                deleted_buildings.append(building_id)
                total_affected_floors += affected_floors
                total_affected_locations += affected_locations

                logger.info(f"Successfully deleted building: {building_id}")

            except Exception as e:
                logger.error(f"Failed to delete building {building_id}: {str(e)}")
                failed_deletions.append(building_id)

        delete_type = "hard" if hard_delete else "soft"
        
        logger.info(f"Bulk {delete_type} delete completed. Success: {len(deleted_buildings)}, Failed: {len(failed_deletions)}")

        response = BulkDeleteResponse(
            deleted_buildings=deleted_buildings,
            failed_deletions=failed_deletions,
            delete_type=delete_type,
            total_affected_floors=total_affected_floors,
            total_affected_locations=total_affected_locations,
            message=f"Bulk {delete_type} delete completed. Deleted: {len(deleted_buildings)}, Failed: {len(failed_deletions)}"
        )

        # Determine response status based on results
        if len(deleted_buildings) == len(delete_data.building_ids):
            status_message = "All buildings deleted successfully"
        elif len(deleted_buildings) > 0:
            status_message = "Partial deletion completed"
        else:
            status_message = "No buildings were deleted"

        return {
            "status": "success" if len(deleted_buildings) > 0 else "warning",
            "message": status_message,
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in bulk delete buildings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform bulk delete: {str(e)}"
        )
