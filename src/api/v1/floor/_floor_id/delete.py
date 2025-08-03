from fastapi import HTTPException, Path, Query, status, Depends, Request
from pydantic import BaseModel
from typing import Optional
import time
import logging
from src.datamodel.database.domain.DigitalSignage import Floor, Location, Building
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db
from sqlalchemy.ext.asyncio import AsyncSession



logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Floor"],
        "summary": "Delete Floor",
        "response_model": dict,
        "description": "Delete a floor by ID. Can perform soft delete (default) or hard delete.",
        "response_description": "Deletion confirmation",
        "deprecated": False,
    }
    return ApiConfig(**config)


class DeleteResponse(BaseModel):
    deleted_id: str
    delete_type: str
    affected_locations: int
    building_updated: bool
    message: str


async def main(
    request: Request,
    floor_id: str = Path(..., description="Floor ID to delete"),
    hard_delete: Optional[bool] = Query(False, description="Perform hard delete (true) or soft delete (false)"),
    cascade: Optional[bool] = Query(True, description="Also delete associated locations"),
    db: AsyncSession = Depends(db)
):
    
    # Get entity_uuid from request
    validate_token_start = time.time()
    validate_token(request)
    # await verify_permissions(request, "content", "write")
    entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid 
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    
    try:
        # Find floor by ID
        floor = await Floor.find_one({
            "floor_id": floor_id
        })
        
        if not floor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Floor with ID '{floor_id}' not found"
            )

        affected_locations = 0
        building_updated = False

        # Handle cascade deletion of locations
        if cascade and floor.locations:
            locations = await Location.find({
                "location_id": {"$in": floor.locations},
                "status": "active"
            }).to_list()
            
            affected_locations = len(locations)
            
            # Delete or soft delete locations
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
                building_updated = True

        # Delete or soft delete floor
        if hard_delete:
            await floor.delete()
            delete_type = "hard"
        else:
            floor.status = "deleted"
            floor.updated_by = None  # Set to current user if available
            floor.update_on = time.time()
            await floor.save()
            delete_type = "soft"

        logger.info(f"Floor {delete_type} deleted: {floor_id}, affected locations: {affected_locations}")

        response = DeleteResponse(
            deleted_id=floor_id,
            delete_type=delete_type,
            affected_locations=affected_locations,
            building_updated=building_updated,
            message=f"Floor {delete_type} deleted successfully"
        )

        return {
            "status": "success",
            "message": f"Floor {delete_type} deleted successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting floor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete floor: {str(e)}"
        )
