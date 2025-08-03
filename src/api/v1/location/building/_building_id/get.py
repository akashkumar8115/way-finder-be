from fastapi import HTTPException, Query, Path, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from src.datamodel.database.domain.DigitalSignage import Location, Floor, Building, LocationType, ShapeType
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Location"],
        "summary": "Get All Locations by Building ID",
        "response_model": dict,
        "description": "Retrieve all locations within a specific building, organized by floors.",
        "response_description": "List of locations grouped by floors",
        "deprecated": False,
    }
    return ApiConfig(**config)


class LocationItem(BaseModel):
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
    status: str

    class Config:
        allow_population_by_field_name = True


class FloorWithLocations(BaseModel):
    floor_id: str
    floor_name: str
    floor_number: int
    floor_plan_url: Optional[str] = None
    locations: List[LocationItem] = []
    total_locations: int = 0

    class Config:
        allow_population_by_field_name = True


class LocationsResponse(BaseModel):
    building_id: str
    building_name: str
    floors: List[FloorWithLocations] = []
    total_floors: int = 0
    total_locations: int = 0


async def main(
    building_id: str = Path(..., description="Building ID to get locations for"),
    floor_id: Optional[str] = Query(None, description="Optional floor ID to filter locations"),
    category: Optional[LocationType] = Query(None, description="Optional category filter"),
    is_published: Optional[bool] = Query(None, description="Filter by published status"),
    include_inactive: bool = Query(False, description="Include inactive locations")
):
    try:
        # Validate building exists
        building = await Building.find_one({
            "building_id": building_id,
            "status": "active"
        })
        
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building with ID '{building_id}' not found"
            )

        # Build location filter
        location_filter = {
            "status": {"$in": ["active", "inactive"] if include_inactive else ["active"]}
        }
        
        if category:
            location_filter["category"] = category
            
        if is_published is not None:
            location_filter["is_published"] = is_published

        # Get floors for the building
        floor_filter = {
            "building_id": building_id,
            "status": "active"
        }
        
        if floor_id:
            floor_filter["floor_id"] = floor_id
            
        floors = await Floor.find(floor_filter).sort("floor_number").to_list()
        
        if not floors:
            return {
                "status": "success",
                "message": "No floors found for this building",
                "data": LocationsResponse(
                    building_id=building_id,
                    building_name=building.name,
                    floors=[],
                    total_floors=0,
                    total_locations=0
                )
            }

        floors_with_locations = []
        total_locations = 0

        # Get locations for each floor
        for floor in floors:
            # Add floor_id to location filter
            floor_location_filter = {**location_filter, "floor_id": floor.floor_id}
            
            # Get locations for this floor
            locations = await Location.find(floor_location_filter).to_list()
            
            # Convert locations to response format
            location_items = []
            for location in locations:
                location_item = LocationItem(
                    location_id=location.location_id,
                    name=location.name,
                    category=location.category.value,
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
                    status=location.status
                )
                location_items.append(location_item)

            # Create floor with locations
            floor_with_locations = FloorWithLocations(
                floor_id=floor.floor_id,
                floor_name=floor.name,
                floor_number=floor.floor_number,
                floor_plan_url=floor.floor_plan_url,
                locations=location_items,
                total_locations=len(location_items)
            )
            
            floors_with_locations.append(floor_with_locations)
            total_locations += len(location_items)

        # Prepare response
        response = LocationsResponse(
            building_id=building_id,
            building_name=building.name,
            floors=floors_with_locations,
            total_floors=len(floors_with_locations),
            total_locations=total_locations
        )

        logger.info(f"Retrieved {total_locations} locations across {len(floors_with_locations)} floors for building: {building_id}")

        return {
            "status": "success",
            "message": f"Retrieved locations for building '{building.name}'",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving locations for building {building_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve locations: {str(e)}"
        )
