from fastapi import HTTPException, Depends, status
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
import time
import logging
from src.datamodel.database.domain.DigitalSignage import Location, ShapeType, LocationType
from src.datamodel.datavalidation.apiconfig import ApiConfig


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Location"],
        "summary": "Bulk Update Locations",
        "response_model": dict,
        "description": "Update multiple location tags at once including size, shape, color and position.",
        "response_description": "Bulk update results with success and failure details",
        "deprecated": False,
    }
    return ApiConfig(**config)


class LocationUpdateData(BaseModel):
    location_id: str = Field(..., description="ID of the location to update")
    name: Optional[str] = Field(None, description="Name of the location")
    category: Optional[LocationType] = Field(None, description="Category of the location")
    shape: Optional[ShapeType] = Field(None, description="Shape type - circle or rectangle")
    x: Optional[float] = Field(None, description="X coordinate position")
    y: Optional[float] = Field(None, description="Y coordinate position")
    width: Optional[float] = Field(None, description="Width for rectangle shape")
    height: Optional[float] = Field(None, description="Height for rectangle shape")
    radius: Optional[float] = Field(None, description="Radius for circle shape")
    logo_url: Optional[str] = Field(None, alias="logoUrl", description="URL for location logo/icon")
    color: Optional[str] = Field(None, description="Color for location display")
    text_color: Optional[str] = Field(None, description="Text color for location")
    is_published: Optional[bool] = Field(None, description="Whether location is published")
    description: Optional[str] = Field(None, description="Description of the location")

    @validator('color', 'text_color')
    def validate_color_format(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be in hex format (e.g., #3b82f6)')
        if v and len(v) != 7:
            raise ValueError('Color must be 7 characters long including # (e.g., #3b82f6)')
        return v

    class Config:
        allow_population_by_field_name = True


class BulkLocationUpdateRequest(BaseModel):
    locations: List[LocationUpdateData] = Field(..., description="List of locations to update")
    updated_by: Optional[str] = Field(None, description="User who is performing the update")

    @validator('locations')
    def validate_locations_not_empty(cls, v):
        if not v:
            raise ValueError('At least one location must be provided for update')
        if len(v) > 100:  # Reasonable limit for bulk operations
            raise ValueError('Maximum 100 locations can be updated at once')
        return v


class LocationUpdateResult(BaseModel):
    location_id: str
    status: str  # "success" or "failed"
    message: str
    updated_fields: Optional[List[str]] = None


class BulkUpdateResponse(BaseModel):
    total_requested: int
    successful_updates: int
    failed_updates: int
    results: List[LocationUpdateResult]


async def validate_shape_requirements(location_data: LocationUpdateData, existing_location: Location) -> None:
    """Validate shape-specific requirements for location update"""
    shape = location_data.shape if location_data.shape is not None else existing_location.shape
    
    if shape == ShapeType.RECTANGLE:
        width = location_data.width if location_data.width is not None else existing_location.width
        height = location_data.height if location_data.height is not None else existing_location.height
        
        if not width or not height:
            raise ValueError("Width and height are required for rectangle shape")
    
    elif shape == ShapeType.CIRCLE:
        radius = location_data.radius if location_data.radius is not None else existing_location.radius
        
        if not radius:
            raise ValueError("Radius is required for circle shape")


async def update_single_location(location_data: LocationUpdateData, updated_by: Optional[str]) -> LocationUpdateResult:
    """Update a single location and return the result"""
    try:
        # Find the existing location
        existing_location = await Location.find_one({
            "location_id": location_data.location_id,
            "status": "active"
        })
        
        if not existing_location:
            return LocationUpdateResult(
                location_id=location_data.location_id,
                status="failed",
                message=f"Location with ID '{location_data.location_id}' not found"
            )
        
        # Validate shape requirements
        await validate_shape_requirements(location_data, existing_location)
        
        # Check for name conflicts if name is being updated
        if location_data.name and location_data.name != existing_location.name:
            name_conflict = await Location.find_one({
                "name": location_data.name,
                "floor_id": existing_location.floor_id,
                "status": "active",
                "location_id": {"$ne": location_data.location_id}
            })
            
            if name_conflict:
                return LocationUpdateResult(
                    location_id=location_data.location_id,
                    status="failed",
                    message=f"Location with name '{location_data.name}' already exists on this floor"
                )
        
        # Track updated fields
        updated_fields = []
        
        # Update fields that are provided
        update_data = {}
        
        if location_data.name is not None:
            update_data["name"] = location_data.name
            updated_fields.append("name")
        
        if location_data.category is not None:
            update_data["category"] = location_data.category
            updated_fields.append("category")
        
        if location_data.shape is not None:
            update_data["shape"] = location_data.shape
            updated_fields.append("shape")
        
        if location_data.x is not None:
            update_data["x"] = location_data.x
            updated_fields.append("x")
        
        if location_data.y is not None:
            update_data["y"] = location_data.y
            updated_fields.append("y")
        
        if location_data.width is not None:
            update_data["width"] = location_data.width
            updated_fields.append("width")
        
        if location_data.height is not None:
            update_data["height"] = location_data.height
            updated_fields.append("height")
        
        if location_data.radius is not None:
            update_data["radius"] = location_data.radius
            updated_fields.append("radius")
        
        if location_data.logo_url is not None:
            update_data["logo_url"] = location_data.logo_url
            updated_fields.append("logo_url")
        
        if location_data.color is not None:
            update_data["color"] = location_data.color
            updated_fields.append("color")
        
        if location_data.text_color is not None:
            update_data["text_color"] = location_data.text_color
            updated_fields.append("text_color")
        
        if location_data.is_published is not None:
            update_data["is_published"] = location_data.is_published
            updated_fields.append("is_published")
        
        if location_data.description is not None:
            update_data["description"] = location_data.description
            updated_fields.append("description")
        
        # Add update metadata
        update_data["updated_by"] = updated_by
        update_data["update_on"] = time.time()
        updated_fields.extend(["updated_by", "update_on"])
        
        # Perform the update
        await existing_location.update({"$set": update_data})
        
        return LocationUpdateResult(
            location_id=location_data.location_id,
            status="success",
            message="Location updated successfully",
            updated_fields=updated_fields
        )
        
    except ValueError as ve:
        return LocationUpdateResult(
            location_id=location_data.location_id,
            status="failed",
            message=str(ve)
        )
    except Exception as e:
        logger.exception(f"Error updating location {location_data.location_id}: {str(e)}")
        return LocationUpdateResult(
            location_id=location_data.location_id,
            status="failed",
            message=f"Internal error: {str(e)}"
        )


async def main(
    bulk_update_data: BulkLocationUpdateRequest,
):
    try:
        logger.info(f"Starting bulk update for {len(bulk_update_data.locations)} locations")
        
        results = []
        successful_updates = 0
        failed_updates = 0
        
        # Process each location update
        for location_data in bulk_update_data.locations:
            result = await update_single_location(location_data, bulk_update_data.updated_by)
            results.append(result)
            
            if result.status == "success":
                successful_updates += 1
            else:
                failed_updates += 1
        
        # Prepare response
        response = BulkUpdateResponse(
            total_requested=len(bulk_update_data.locations),
            successful_updates=successful_updates,
            failed_updates=failed_updates,
            results=results
        )
        
        logger.info(f"Bulk update completed: {successful_updates} successful, {failed_updates} failed")
        
        return {
            "status": "completed",
            "message": f"Bulk update completed: {successful_updates} successful, {failed_updates} failed",
            "data": response
        }
        
    except Exception as e:
        logger.exception(f"Error in bulk location update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform bulk update: {str(e)}"
        )
