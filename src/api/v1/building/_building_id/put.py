from fastapi import HTTPException, Depends, status, Request
from pydantic import BaseModel, Field
from typing import Optional
import time
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from src.datamodel.database.domain.DigitalSignage import Building
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Building"],
        "summary": "Update Building",
        "response_model": dict,
        "description": "Update an existing building in the way-finder system.",
        "response_description": "Updated building data",
        "deprecated": False,
    }
    return ApiConfig(**config)


class BuildingUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Name of the building")
    address: Optional[str] = Field(None, description="Building address")
    description: Optional[str] = Field(None, description="Description of the building")
    status: Optional[str] = Field(None, description="Building status (active/inactive)")

    class Config:
        allow_population_by_field_name = True


class BuildingResponse(BaseModel):
    building_id: str
    name: str
    address: Optional[str] = None
    floors: list = []
    description: Optional[str] = None
    entity_uuid: Optional[str] = None
    datetime: float
    update_on: Optional[float] = None
    updated_by: Optional[str] = None
    status: str

    class Config:
        allow_population_by_field_name = True


async def main(
    request: Request,
    building_id: str,
    building_data: BuildingUpdateRequest,
    db: AsyncSession = Depends(db)
):
    """Main handler for building updates"""
    # Validate token and get user info
    validate_token_start = time.time()
    validate_token(request)
    entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    try:
        # Find the existing building
        existing_building = await Building.find_one({
            "building_id": building_id,
            "entity_uuid": entity_uuid,
            "status": {"$ne": "deleted"}  # Exclude deleted buildings
        })
        
        if not existing_building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building with ID '{building_id}' not found"
            )

        # Check if name is being updated and if it conflicts with existing buildings
        if building_data.name and building_data.name != existing_building.name:
            name_conflict = await Building.find_one({
                "name": building_data.name,
                "entity_uuid": entity_uuid,
                "building_id": {"$ne": building_id},  # Exclude current building
                "status": "active"
            })
            
            if name_conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Building with name '{building_data.name}' already exists"
                )

        # Update only provided fields
        update_data = {}
        if building_data.name is not None:
            update_data["name"] = building_data.name
        if building_data.address is not None:
            update_data["address"] = building_data.address
        if building_data.description is not None:
            update_data["description"] = building_data.description
        if building_data.status is not None:
            # Validate status values
            if building_data.status not in ["active", "inactive"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Status must be either 'active' or 'inactive'"
                )
            update_data["status"] = building_data.status

        # Add update metadata
        update_data["update_on"] = time.time()
        update_data["updated_by"] = user_uuid

        # Update the building
        await existing_building.update({"$set": update_data})
        
        # Refresh the building data
        updated_building = await Building.find_one({"building_id": building_id})
        
        logger.info(f"Building updated successfully: {building_id}")

        # Prepare response
        response = BuildingResponse(
            building_id=updated_building.building_id,
            name=updated_building.name,
            address=updated_building.address,
            floors=updated_building.floors or [],
            entity_uuid=updated_building.entity_uuid,
            description=updated_building.description,
            datetime=updated_building.datetime,
            update_on=updated_building.update_on,
            updated_by=updated_building.updated_by,
            status=updated_building.status
        )

        return {
            "status": "success",
            "message": "Building updated successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating building: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update building: {str(e)}"
        )
