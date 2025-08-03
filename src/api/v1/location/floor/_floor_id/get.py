from fastapi import HTTPException, Path, Query, status
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
        "tags": ["Location"],
        "summary": "Get Locations by Floor ID",
        "response_model": dict,
        "description": "Retrieve all locations for a specific floor.",
        "response_description": "List of locations for the floor",
        "deprecated": False,
    }
    return ApiConfig(**config)


class LocationResponse(BaseModel):
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
    logo_url: Optional[str] = None
    color: str
    text_color: str
    is_published: bool
    description: Optional[str] = None
    created_by: Optional[str] = None
    datetime: float
    updated_by: Optional[str] = None
    update_on: Optional[float] = None
    status: str

    class Config:
        allow_population_by_field_name = True


class FloorLocationsResponse(BaseModel):
    floor_id: str
    floor_name: str
    floor_number: int
    building_id: Optional[str] = None
    total_locations: int
    locations: List[LocationResponse]

    class Config:
        allow_population_by_field_name = True


async def main(
    floor_id: str = Path(..., description="Floor ID to get locations for"),
    status_filter: Optional[str] = Query("active", description="Filter by status (active, inactive, all)"),
    category: Optional[str] = Query(None, description="Filter by location category"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    skip: Optional[int] = Query(0, description="Skip number of results for pagination")
):
    try:
        # First, verify that the floor exists
        floor = await Floor.find_one({
            "floor_id": floor_id
        })
        
        if not floor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Floor with ID '{floor_id}' not found"
            )

        # Build query filter for locations - use floor_id directly instead of floor.locations
        query_filter = {"floor_id": floor_id}
        
        if status_filter and status_filter != "all":
            query_filter["status"] = status_filter
            
        if category:
            query_filter["category"] = {"$regex": category, "$options": "i"}

        # Execute query to get locations
        query = Location.find(query_filter).sort("name")  # Sort by name
        
        if skip:
            query = query.skip(skip)
        if limit:
            query = query.limit(limit)
            
        locations = await query.to_list()
        
        # Prepare response
        location_list = []
        for location in locations:
            location_response = LocationResponse(
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
                status=location.status
            )
            location_list.append(location_response)

        # Create comprehensive response
        response = FloorLocationsResponse(
            floor_id=floor.floor_id,
            floor_name=floor.name,
            floor_number=floor.floor_number,
            building_id=floor.building_id,
            total_locations=len(location_list),
            locations=location_list
        )

        logger.info(f"Retrieved {len(location_list)} locations for floor: {floor_id}")

        return {
            "status": "success",
            "message": f"Retrieved {len(location_list)} locations for floor '{floor.name}'",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving locations for floor {floor_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve locations for floor: {str(e)}"
        )
