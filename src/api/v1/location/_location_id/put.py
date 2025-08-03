from fastapi import HTTPException, Path, status
from pydantic import BaseModel, Field, validator
from typing import Optional
import time
import logging
from src.datamodel.database.domain.DigitalSignage import Location, Floor, ShapeType
from src.datamodel.datavalidation.apiconfig import ApiConfig


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Location"],
        "summary": "Update Location (Full)",
        "response_model": dict,
        "description": "Completely update a location with new data. All fields are required. Handles floor relationship changes.",
        "response_description": "Updated location data",
        "deprecated": False,
    }
    return ApiConfig(**config)


class LocationUpdateRequest(BaseModel):
    name: str = Field(..., description="Name of the location")
    category: str = Field(..., description="Category of the location")
    floor_id: str = Field(..., description="ID of the floor this location belongs to")
    shape: ShapeType = Field(..., description="Shape type - circle or rectangle")
    x: float = Field(..., description="X coordinate position")
    y: float = Field(..., description="Y coordinate position")
    width: Optional[float] = Field(None, description="Width for rectangle shape")
    height: Optional[float] = Field(None, description="Height for rectangle shape")
    radius: Optional[float] = Field(None, description="Radius for circle shape")
    logo_url: Optional[str] = Field(None, alias="logoUrl", description="URL for location logo/icon")
    color: str = Field(..., description="Color for location")
    text_color: str = Field(..., description="Text color for location")
    is_published: bool = Field(default=True, description="Whether the location is published")
    description: Optional[str] = Field(None, description="Description of the location")
    status: str = Field(default="active", description="Status of the location")

    @validator('width', 'height')
    def validate_rectangle_dimensions(cls, v, values):
        if values.get('shape') == ShapeType.RECTANGLE and v is None:
            raise ValueError('Width and height are required for rectangle shape')
        return v

    @validator('radius')
    def validate_circle_radius(cls, v, values):
        if values.get('shape') == ShapeType.CIRCLE and v is None:
            raise ValueError('Radius is required for circle shape')
        return v

    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['active', 'inactive', 'deleted']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {allowed_statuses}')
        return v

    class Config:
        allow_population_by_field_name = True


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
    update_on: float
    status: str

    class Config:
        allow_population_by_field_name = True


async def main(
    location_data: LocationUpdateRequest,
    location_id: str = Path(..., description="Location ID to update"),
):
    try:
        # Find existing location
        existing_location = await Location.find_one({
            "location_id": location_id
        })
        
        if not existing_location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location with ID '{location_id}' not found"
            )

        # Store original floor_id for potential floor updates
        original_floor_id = existing_location.floor_id
        floor_changed = location_data.floor_id != original_floor_id

        # Validate that the new floor exists and is active
        new_floor = await Floor.find_one({
            "floor_id": location_data.floor_id,
            "status": "active"
        })
        
        if not new_floor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Floor with ID '{location_data.floor_id}' not found or inactive"
            )

        # Check if another location with the same name exists on the target floor (excluding current location)
        name_check = await Location.find_one({
            "name": location_data.name,
            "floor_id": location_data.floor_id,
            "location_id": {"$ne": location_id},
            "status": {"$ne": "deleted"}
        })
        
        if name_check:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Another location with name '{location_data.name}' already exists on this floor"
            )

        # # Validate shape-specific requirements
        # if location_data.shape == ShapeType.RECTANGLE:
        #     if not location_data.width or not location_data.height:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="Width and height are required for rectangle shape"
        #         )
        # elif location_data.shape == ShapeType.CIRCLE:
        #     if not location_data.radius:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="Radius is required for circle shape"
        #         )

        # Handle floor relationship changes
        if floor_changed:
            # Remove location from old floor's locations list
            if original_floor_id:
                old_floor = await Floor.find_one({
                    "floor_id": original_floor_id,
                    "status": "active"
                })
                
                if old_floor and location_id in old_floor.locations:
                    old_floor.locations.remove(location_id)
                    old_floor.updated_by = None  # Set to current user if available
                    old_floor.update_on = time.time()
                    await old_floor.save()
                    logger.info(f"Removed location {location_id} from old floor {original_floor_id}")

            # Add location to new floor's locations list
            if location_id not in new_floor.locations:
                new_floor.locations.append(location_id)
                new_floor.updated_by = None  # Set to current user if available
                new_floor.update_on = time.time()
                await new_floor.save()
                logger.info(f"Added location {location_id} to new floor {location_data.floor_id}")

        # Update all fields
        existing_location.name = location_data.name
        existing_location.category = location_data.category
        existing_location.floor_id = location_data.floor_id
        existing_location.shape = location_data.shape
        existing_location.x = location_data.x
        existing_location.y = location_data.y
        existing_location.width = location_data.width
        existing_location.height = location_data.height
        existing_location.radius = location_data.radius
        existing_location.logo_url = location_data.logo_url
        existing_location.color = location_data.color
        existing_location.text_color = location_data.text_color
        existing_location.is_published = location_data.is_published
        existing_location.description = location_data.description
        existing_location.status = location_data.status
        existing_location.updated_by = None  # Set to current user if available
        existing_location.update_on = time.time()

        # Save to database
        await existing_location.save()
        
        logger.info(f"Location updated successfully: {location_id}, floor_changed: {floor_changed}")

        # Prepare response
        response = LocationResponse(
            location_id=existing_location.location_id,
            name=existing_location.name,
            category=existing_location.category,
            floor_id=existing_location.floor_id,
            shape=existing_location.shape.value,
            x=existing_location.x,
            y=existing_location.y,
            width=existing_location.width,
            height=existing_location.height,
            radius=existing_location.radius,
            logo_url=existing_location.logo_url,
            color=existing_location.color,
            text_color=existing_location.text_color,
            is_published=existing_location.is_published,
            description=existing_location.description,
            created_by=existing_location.created_by,
            datetime=existing_location.datetime,
            updated_by=existing_location.updated_by,
            update_on=existing_location.update_on,
            status=existing_location.status
        )

        return {
            "status": "success",
            "message": "Location updated successfully",
            "data": response,
            "floor_changed": floor_changed,
            "original_floor_id": original_floor_id if floor_changed else None,
            "new_floor_id": existing_location.floor_id if floor_changed else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating location: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update location: {str(e)}"
        )
