from fastapi import HTTPException, Path, status, Query
from pydantic import BaseModel, Field
from typing import Optional
import logging
from src.datamodel.database.domain.DigitalSignage import Location, Floor, Building
from src.datamodel.datavalidation.apiconfig import ApiConfig


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Location"],
        "summary": "Get Location by ID",
        "response_model": dict,
        "description": "Retrieve a specific location by its ID with detailed information including floor and building context.",
        "response_description": "Location details with context",
        "deprecated": False,
    }
    return ApiConfig(**config)


class FloorContext(BaseModel):
    floor_id: str
    floor_name: str
    floor_number: int
    building_id: Optional[str] = None

    class Config:
        allow_population_by_field_name = True


class BuildingContext(BaseModel):
    building_id: str
    building_name: str
    address: Optional[str] = None

    class Config:
        allow_population_by_field_name = True


class LocationDetailResponse(BaseModel):
    location_id: str
    name: str
    category: str
    floor_id: str
    shape: str
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None
    logo_url: Optional[str] = Field(None, alias="logoUrl")
    color: str
    text_color: str
    is_published: bool
    description: Optional[str] = None
    created_by: Optional[str] = None
    datetime: float
    updated_by: Optional[str] = None
    update_on: Optional[float] = None
    status: str
    floor_context: Optional[FloorContext] = None
    building_context: Optional[BuildingContext] = None
    metadata: Optional[dict] = None

    class Config:
        allow_population_by_field_name = True


async def main(
    location_id: str = Path(..., description="Location ID to retrieve"),
    include_context: Optional[bool] = Query(True, description="Include floor and building context information")
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

        floor_context = None
        building_context = None

        # Get context information if requested
        if include_context and location.floor_id:
            # Find floor using the floor_id from location
            floor = await Floor.find_one({
                "floor_id": location.floor_id,
                "status": "active"
            })
            
            if floor:
                floor_context = FloorContext(
                    floor_id=floor.floor_id,
                    floor_name=floor.name,
                    floor_number=floor.floor_number,
                    building_id=floor.building_id
                )
                
                # Find building if floor has building_id
                if floor.building_id:
                    building = await Building.find_one({
                        "building_id": floor.building_id,
                        "status": "active"
                    })
                    
                    if building:
                        building_context = BuildingContext(
                            building_id=building.building_id,
                            building_name=building.name,
                            address=building.address
                        )
            else:
                logger.warning(f"Floor with ID {location.floor_id} not found or inactive for location {location_id}")

        # Prepare response
        response = LocationDetailResponse(
            location_id=location.location_id,
            name=location.name,
            category=location.category,
            floor_id=location.floor_id,
            shape=location.shape.value,
            x=location.x,
            y=location.y,
            width=location.width,
            height=location.height,
            radius=location.radius,
            logo_url=location.logo_url,
            color=location.color,
            text_color=location.text_color,
            is_published=location.is_published,
            description=location.description,
            created_by=location.created_by,
            datetime=location.datetime,
            updated_by=location.updated_by,
            update_on=location.update_on,
            status=location.status,
            floor_context=floor_context,
            building_context=building_context,
            metadata=location.metadata
        )

        logger.info(f"Retrieved location details: {location_id} from floor: {location.floor_id}")

        return {
            "status": "success",
            "message": "Location retrieved successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving location: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve location: {str(e)}"
        )
