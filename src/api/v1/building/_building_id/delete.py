from fastapi import HTTPException, Path, Query, status
from pydantic import BaseModel
from typing import Optional
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
        "summary": "Delete Building",
        "response_model": dict,
        "description": "Delete a building by ID. Can perform soft delete (default) or hard delete.",
        "response_description": "Deletion confirmation",
        "deprecated": False,
    }
    return ApiConfig(**config)


class DeleteResponse(BaseModel):
    deleted_id: str
    delete_type: str
    affected_floors: int
    affected_locations: int
    message: str


async def main(
    building_id: str = Path(..., description="Building ID to delete"),
    hard_delete: Optional[bool] = Query(False, description="Perform hard delete (true) or soft delete (false)"),
    cascade: Optional[bool] = Query(True, description="Also delete associated floors and locations")
):
    try:
        # Find building by ID
        building = await Building.find_one({
            "building_id": building_id
        })
        
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building with ID '{building_id}' not found"
            )

        affected_floors = 0
        affected_locations = 0

        # Handle cascade deletion of floors and locations
        if cascade and building.floors:
            # Get all floors in this building
            floors = await Floor.find({
                "building_id": building_id,
                "status": "active"
            }).to_list()
            
            affected_floors = len(floors)
            
            for floor in floors:
                # Handle locations in each floor
                if floor.locations:
                    locations = await Location.find({
                        "location_id": {"$in": floor.locations},
                        "status": "active"
                    }).to_list()
                    
                    affected_locations += len(locations)
                    
                    # Delete or soft delete locations
                    for location in locations:
                        if hard_delete:
                            await location.delete()
                        else:
                            location.status = "deleted"
                            location.updated_by = None  # Set to current user if available
                            location.update_on = time.time()
                            await location.save()
                
                # Delete or soft delete floor
                if hard_delete:
                    await floor.delete()
                else:
                    floor.status = "deleted"
                    floor.updated_by = None  # Set to current user if available
                    floor.update_on = time.time()
                    await floor.save()

        # Delete or soft delete building
        if hard_delete:
            await building.delete()
            delete_type = "hard"
        else:
            building.status = "deleted"
            building.updated_by = None  # Set to current user if available
            building.update_on = time.time()
            await building.save()
            delete_type = "soft"

        logger.info(f"Building {delete_type} deleted: {building_id}, affected floors: {affected_floors}, affected locations: {affected_locations}")

        response = DeleteResponse(
            deleted_id=building_id,
            delete_type=delete_type,
            affected_floors=affected_floors,
            affected_locations=affected_locations,
            message=f"Building {delete_type} deleted successfully"
        )

        return {
            "status": "success",
            "message": f"Building {delete_type} deleted successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting building: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete building: {str(e)}"
        )
