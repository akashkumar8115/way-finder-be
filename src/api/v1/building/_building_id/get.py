from fastapi import HTTPException, Path, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from src.datamodel.database.domain.DigitalSignage import Building, Floor
from src.datamodel.datavalidation.apiconfig import ApiConfig


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Building"],
        "summary": "Get Building by ID",
        "response_model": dict,
        "description": "Retrieve a specific building by its ID with detailed floor information.",
        "response_description": "Building details with floors",
        "deprecated": False,
    }
    return ApiConfig(**config)


class FloorDetailResponse(BaseModel):
    floor_id: str
    name: str
    floor_number: int
    floor_plan_url: Optional[str] = None
    locations_count: int
    description: Optional[str] = None
    datetime: float
    status: str

    class Config:
        allow_population_by_field_name = True


class BuildingDetailResponse(BaseModel):
    building_id: str
    name: str
    address: Optional[str] = None
    floors: List[FloorDetailResponse] = []
    description: Optional[str] = None
    created_by: Optional[str] = None
    datetime: float
    updated_by: Optional[str] = None
    update_on: Optional[float] = None
    status: str

    class Config:
        allow_population_by_field_name = True


async def main(
    building_id: str = Path(..., description="Building ID to retrieve")
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

        # Get detailed floor information
        floor_details = []
        if building.floors:
            floors = await Floor.find({
                "floor_id": {"$in": building.floors},
                "status": "active"
            }).to_list()
            
            # Sort floors by floor_number
            floors.sort(key=lambda x: x.floor_number)
            
            for floor in floors:
                floor_detail = FloorDetailResponse(
                    floor_id=floor.floor_id,
                    name=floor.name,
                    floor_number=floor.floor_number,
                    floor_plan_url=floor.floor_plan_url,
                    locations_count=len(floor.locations) if floor.locations else 0,
                    description=floor.description,
                    datetime=floor.datetime,
                    status=floor.status
                )
                floor_details.append(floor_detail)

        # Prepare response
        response = BuildingDetailResponse(
            building_id=building.building_id,
            name=building.name,
            address=building.address,
            floors=floor_details,
            description=building.description,
            created_by=building.created_by,
            datetime=building.datetime,
            updated_by=building.updated_by,
            update_on=building.update_on,
            status=building.status
        )

        logger.info(f"Retrieved building details: {building_id}")

        return {
            "status": "success",
            "message": "Building retrieved successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving building: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve building: {str(e)}"
        )
