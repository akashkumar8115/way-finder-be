from fastapi import HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from src.datamodel.database.domain.DigitalSignage import Location, ShapeType
from src.datamodel.datavalidation.apiconfig import ApiConfig


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Location"],
        "summary": "Get All Locations",
        "response_model": dict,
        "description": "Retrieve all locations with optional filtering by category, shape, status, floor, etc.",
        "response_description": "List of locations",
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

    class Config:
        allow_population_by_field_name = True


async def main(
    status_filter: Optional[str] = Query("active", description="Filter by status (active, inactive, deleted, all)"),
    category: Optional[str] = Query(None, description="Filter by location category"),
    floor_id: Optional[str] = Query(None, description="Filter by floor ID"),
    shape: Optional[ShapeType] = Query(None, description="Filter by shape type (circle, rectangle)"),
    name: Optional[str] = Query(None, description="Filter by location name (partial match)"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    skip: Optional[int] = Query(0, description="Skip number of results for pagination"),
    sort_by: Optional[str] = Query("name", description="Sort by field (name, category, datetime, floor_id)"),
    sort_order: Optional[str] = Query("asc", description="Sort order (asc, desc)")
):
    try:
        # Build query filter
        query_filter = {}
        
        if status_filter and status_filter != "all":
            query_filter["status"] = status_filter
        
        if category:
            query_filter["category"] = {"$regex": category, "$options": "i"}  # Case-insensitive partial match
            
        if floor_id:
            query_filter["floor_id"] = floor_id
            
        if shape:
            query_filter["shape"] = shape
        
        if name:
            query_filter["name"] = {"$regex": name, "$options": "i"}  # Case-insensitive partial match

        # Execute query with sorting
        sort_direction = 1 if sort_order.lower() == "asc" else -1
        query = Location.find(query_filter).sort([(sort_by, sort_direction)])
        
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

        logger.info(f"Retrieved {len(location_list)} locations")

        return {
            "status": "success",
            "message": f"Retrieved {len(location_list)} locations",
            "data": location_list,
            "total": len(location_list),
            "filters_applied": {
                "status": status_filter,
                "category": category,
                "floor_id": floor_id,
                "shape": shape.value if shape else None,
                "name": name
            }
        }

    except Exception as e:
        logger.exception(f"Error retrieving locations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve locations: {str(e)}"
        )
