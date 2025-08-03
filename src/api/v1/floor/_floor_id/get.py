from fastapi import HTTPException, Path, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from src.datamodel.database.domain.DigitalSignage import Floor, Location
from src.datamodel.datavalidation.apiconfig import ApiConfig


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Floor"],
        "summary": "Get Floor by ID",
        "response_model": dict,
        "description": "Retrieve a specific floor by its ID with detailed location information.",
        "response_description": "Floor details with locations",
        "deprecated": False,
    }
    return ApiConfig(**config)


class LocationDetailResponse(BaseModel):
    location_id: str
    name: str
    category: str
    shape: str
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    status: str

    class Config:
        allow_population_by_field_name = True


class FloorDetailResponse(BaseModel):
    floor_id: str
    name: str
    building_id: Optional[str] = None
    floor_number: int
    floor_plan_url: Optional[str] = None
    locations: List[LocationDetailResponse] = []
    description: Optional[str] = None
    created_by: Optional[str] = None
    datetime: float
    updated_by: Optional[str] = None
    update_on: Optional[float] = None
    status: str

    class Config:
        allow_population_by_field_name = True


async def main(
    floor_id: str = Path(..., description="Floor ID to retrieve")
):
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

        # Get detailed location information
        location_details = []
        if floor.locations:
            locations = await Location.find({
                "location_id": {"$in": floor.locations},
                "status": "active"
            }).to_list()
            
            for location in locations:
                location_detail = LocationDetailResponse(
                    location_id=location.location_id,
                    name=location.name,
                    category=location.category,
                    shape=location.shape.value,
                    x=location.x,
                    y=location.y,
                    width=location.width,
                    height=location.height,
                    radius=location.radius,
                    logo_url=location.logo_url,
                    description=location.description,
                    status=location.status
                )
                location_details.append(location_detail)

        # Prepare response
        response = FloorDetailResponse(
            floor_id=floor.floor_id,
            name=floor.name,
            building_id=floor.building_id,
            floor_number=floor.floor_number,
            floor_plan_url=floor.floor_plan_url,
            locations=location_details,
            description=floor.description,
            created_by=floor.created_by,
            datetime=floor.datetime,
            updated_by=floor.updated_by,
            update_on=floor.update_on,
            status=floor.status
        )

        logger.info(f"Retrieved floor details: {floor_id}")

        return {
            "status": "success",
            "message": "Floor retrieved successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving floor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve floor: {str(e)}"
        )
