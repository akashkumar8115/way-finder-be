from fastapi import HTTPException, Depends, status
from pydantic import BaseModel, Field, validator
from typing import Optional
import time
import logging
from src.datamodel.database.domain.DigitalSignage import Location, ShapeType, LocationType
from src.datamodel.datavalidation.apiconfig import ApiConfig


logger = logging.getLogger(__name__)


def api_config():
        config = {
            "path": "",
            "status_code": 201,
            "tags": ["Location"],
            "summary": "Create Location",
            "response_model": dict,
            "description": "Create a new location for the way-finder system.",
            "response_description": "Created location data",
            "deprecated": False,
        }
        return ApiConfig(**config)



class LocationCreateRequest(BaseModel):
    name: str = Field(..., description="Name of the location")
    category: LocationType = Field(..., description="Category of the location")
    floor_id: str = Field(..., description="ID of the floor this location belongs to")
    shape: ShapeType = Field(..., description="Shape type - circle or rectangle")
    x: float = Field(..., description="X coordinate position")
    y: float = Field(..., description="Y coordinate position")
    width: Optional[float] = Field(None, description="Width for rectangle shape")
    height: Optional[float] = Field(None, description="Height for rectangle shape")
    radius: Optional[float] = Field(None, description="Radius for circle shape")
    logo_url: Optional[str] = Field(None, alias="logoUrl", description="URL for location logo/icon")
    color: str = Field(default="#3b82f6", description="Color for location display")  # NEW FIELD
    text_color: str = Field(default="#000000", description="Text color for location")  # NEW FIELD
    is_published: bool = Field(default=True, description="Whether location is published")  # NEW FIELD
    description: Optional[str] = Field(None, description="Description of the location")

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
    
    @validator('color', 'text_color')  # NEW VALIDATOR
    def validate_color_format(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be in hex format (e.g., #3b82f6)')
        if v and len(v) != 7:
            raise ValueError('Color must be 7 characters long including # (e.g., #3b82f6)')
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
    color: str  # NEW FIELD
    text_color: str  # NEW FIELD
    is_published: bool  # NEW FIELD
    description: Optional[str] = None
    created_by: Optional[str] = None
    datetime: float
    status: str

    class Config:
        allow_population_by_field_name = True


async def main(
    location_data: LocationCreateRequest,
):
    try:
        # Validate shape-specific requirements
        if location_data.shape == ShapeType.RECTANGLE:
            if not location_data.width or not location_data.height:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Width and height are required for rectangle shape"
                )
        elif location_data.shape == ShapeType.CIRCLE:
            if not location_data.radius:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Radius is required for circle shape"
                )
            

        # Check if floor exists (NEW VALIDATION)
        from src.datamodel.database.domain.DigitalSignage import Floor
        floor = await Floor.find_one({
            "floor_id": location_data.floor_id,
            "status": "active"
        })
        
        if not floor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Floor with ID '{location_data.floor_id}' not found"
            )    

        # Check if location with same name exists on the same floor
        existing_location = await Location.find_one({
            "name": location_data.name,
            "floor_id": location_data.floor_id,
            "status": "active"
        })
        
        if existing_location:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Location with name '{location_data.name}' already exists on this floor"
            )

        # Create new location
        new_location = Location(
            name=location_data.name,
            category=location_data.category,
            floor_id=location_data.floor_id,
            shape=location_data.shape,
            x=location_data.x,
            y=location_data.y,
            width=location_data.width,
            height=location_data.height,
            radius=location_data.radius,
            logo_url=location_data.logo_url,
            color=location_data.color,  # NEW FIELD
            text_color=location_data.text_color,  # NEW FIELD
            is_published=location_data.is_published,  # NEW FIELD
            description=location_data.description,
            datetime=time.time(),
            status="active"
        )

        # Save to database
        await new_location.insert()

        # Update floor's locations list (NEW FUNCTIONALITY)
        if new_location.location_id not in floor.locations:
            floor.locations.append(new_location.location_id)
            # floor.updated_by = location_data.created_by
            floor.update_on = time.time()
            await floor.save()
        
        logger.info(f"Location created successfully: {new_location.location_id} on floor: {location_data.floor_id}")

        # Prepare response
        response = LocationResponse(
            location_id=new_location.location_id,
            name=new_location.name,
            category=new_location.category.value,
            floor_id=new_location.floor_id,
            shape=new_location.shape.value,
            x=new_location.x,
            y=new_location.y,
            width=new_location.width,
            height=new_location.height,
            radius=new_location.radius,
            logo_url=new_location.logo_url,
            color=new_location.color,  # NEW FIELD
            text_color=new_location.text_color,  # NEW FIELD
            is_published=new_location.is_published,  # NEW FIELD
            description=new_location.description,
            datetime=new_location.datetime,
            status=new_location.status
        )

        return {
            "status": "success",
            "message": "Location created successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating location: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create location: {str(e)}"
        )
