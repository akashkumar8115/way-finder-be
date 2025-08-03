from fastapi import HTTPException, Path, status, Depends, Request
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import time
import logging
from src.datamodel.database.domain.DigitalSignage import Floor, Building, Location
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
        "summary": "Update Floor (Full)",
        "response_model": dict,
        "description": "Completely update a floor with new data. All fields are required.",
        "response_description": "Updated floor data",
        "deprecated": False,
    }
    return ApiConfig(**config)


class FloorUpdateRequest(BaseModel):
    name: str = Field(..., description="Name of the floor")
    building_id: Optional[str] = Field(None, description="Building identifier this floor belongs to")
    floor_number: int = Field(..., description="Floor number")
    floor_plan_url: Optional[str] = Field(None, description="URL to floor plan image")
    locations: Optional[List[str]] = Field(default_factory=list, description="List of location IDs on this floor")
    status: str = Field(default="active", description="Status of the floor")
    description: Optional[str] = Field(None, description="Description of the floor")

    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['active', 'inactive', 'deleted']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {allowed_statuses}')
        return v

    @validator('floor_number')
    def validate_floor_number(cls, v):
        if v < -10 or v > 200:  # Reasonable range for floor numbers
            raise ValueError('Floor number must be between -10 and 200')
        return v

    @validator('locations')
    def validate_locations(cls, v):
        if v and len(v) != len(set(v)):
            raise ValueError('Location IDs must be unique')
        return v

    class Config:
        allow_population_by_field_name = True


class FloorResponse(BaseModel):
    floor_id: str
    name: str
    building_id: Optional[str] = None
    floor_number: int
    floor_plan_url: Optional[str] = None
    locations: Optional[List[str]] = None
    entity_uuid: Optional[str] = None
    datetime: float
    updated_by: Optional[str] = None
    update_on: float
    status: str
    description: Optional[str] = None

    class Config:
        allow_population_by_field_name = True


async def main(
    request: Request,
    floor_data: FloorUpdateRequest,
    floor_id: str = Path(..., description="Floor ID to update"),
    db: AsyncSession = Depends(db)
):
    
    """
    Update an existing floor with new data. All fields are required.
    """
    # Get entity_uuid from request
    validate_token_start = time.time()
    validate_token(request)
    # await verify_permissions(request, "content", "write")
    entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid 
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    try:
        # Find existing floor
        existing_floor = await Floor.find_one({
            "floor_id": floor_id
        })
        
        if not existing_floor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Floor with ID '{floor_id}' not found"
            )

        # Check if another floor with the same name exists in the same building (excluding current floor)
        name_check_filter = {
            "name": floor_data.name,
            "floor_id": {"$ne": floor_id},
            "status": {"$ne": "deleted"}
        }
        
        if floor_data.building_id:
            name_check_filter["building_id"] = floor_data.building_id
            
        name_check = await Floor.find_one(name_check_filter)
        
        if name_check:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Another floor with name '{floor_data.name}' already exists in this building"
            )

        # Check if floor number conflicts in the same building
        if floor_data.building_id:
            floor_number_check = await Floor.find_one({
                "building_id": floor_data.building_id,
                "floor_number": floor_data.floor_number,
                "floor_id": {"$ne": floor_id},
                "status": {"$ne": "deleted"}
            })
            
            if floor_number_check:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Floor number {floor_data.floor_number} already exists in this building"
                )

        # Validate building exists if building_id is provided
        if floor_data.building_id:
            building = await Building.find_one({
                "building_id": floor_data.building_id,
                "status": {"$ne": "deleted"}
            })
            
            if not building:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Building with ID '{floor_data.building_id}' not found"
                )

        # Validate all location IDs exist if provided
        if floor_data.locations:
            for location_id in floor_data.locations:
                location = await Location.find_one({
                    "location_id": location_id,
                    "status": {"$ne": "deleted"}
                })
                
                if not location:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Location with ID '{location_id}' not found"
                    )

        # Handle building relationship changes
        old_building_id = existing_floor.building_id
        new_building_id = floor_data.building_id

        # Remove floor from old building if building changed
        if old_building_id and old_building_id != new_building_id:
            old_building = await Building.find_one({
                "building_id": old_building_id
            })
            
            if old_building and existing_floor.floor_id in old_building.floors:
                old_building.floors.remove(existing_floor.floor_id)
                old_building.updated_by = None  # Set to current user if available
                old_building.update_on = time.time()
                await old_building.save()

        # Add floor to new building if building changed
        if new_building_id and new_building_id != old_building_id:
            new_building = await Building.find_one({
                "building_id": new_building_id
            })
            
            if new_building and existing_floor.floor_id not in new_building.floors:
                new_building.floors.append(existing_floor.floor_id)
                new_building.updated_by = None  # Set to current user if available
                new_building.update_on = time.time()
                await new_building.save()

        # Update all fields
        existing_floor.name = floor_data.name
        existing_floor.building_id = floor_data.building_id
        existing_floor.floor_number = floor_data.floor_number
        existing_floor.floor_plan_url = floor_data.floor_plan_url
        existing_floor.locations = floor_data.locations or []
        existing_floor.status = floor_data.status
        existing_floor.description = floor_data.description
        existing_floor.updated_by = None  # Set to current user if available
        existing_floor.update_on = time.time()

        # Save to database
        await existing_floor.save()
        
        logger.info(f"Floor updated successfully: {floor_id}")

        # Prepare response
        response = FloorResponse(
            floor_id=existing_floor.floor_id,
            name=existing_floor.name,
            building_id=existing_floor.building_id,
            floor_number=existing_floor.floor_number,
            floor_plan_url=existing_floor.floor_plan_url,
            locations=existing_floor.locations,
            entity_uuid=existing_floor.entity_uuid,
            datetime=existing_floor.datetime,
            updated_by=existing_floor.updated_by,
            update_on=existing_floor.update_on,
            status=existing_floor.status,
            description=existing_floor.description
        )

        return {
            "status": "success",
            "message": "Floor updated successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating floor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update floor: {str(e)}"
        )
