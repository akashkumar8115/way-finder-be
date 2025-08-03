from fastapi import HTTPException, Depends, status
from pydantic import BaseModel, Field, validator
from typing import Optional
import time
import logging
from src.datamodel.database.domain.DigitalSignage import VerticalConnector, ShapeType, ConnectorType, Floor
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 201,
        "tags": ["Vertical Connector"],
        "summary": "Create Vertical Connector",
        "response_model": dict,
        "description": "Create a new vertical connector (elevator, stairs, escalator, etc.) for multi-floor navigation.",
        "response_description": "Created vertical connector data",
        "deprecated": False,
    }
    return ApiConfig(**config)

class VerticalConnectorCreateRequest(BaseModel):
    name: str = Field(..., description="Name of the connector (e.g., 'Elevator A', 'Main Stairs')")
    shared_id: str = Field(..., description="Shared identifier across floors (e.g., 'elv-a', 'stairs-1')")
    connector_type: ConnectorType = Field(..., description="Type of vertical connector")
    floor_id: str = Field(..., description="ID of the floor this connector instance belongs to")
    shape: ShapeType = Field(..., description="Shape type - circle or rectangle")
    x: float = Field(..., description="X coordinate position")
    y: float = Field(..., description="Y coordinate position")
    width: Optional[float] = Field(None, description="Width for rectangle shape")
    height: Optional[float] = Field(None, description="Height for rectangle shape")
    radius: Optional[float] = Field(None, description="Radius for circle shape")
    color: str = Field(default="#8b5cf6", description="Color for connector display")
    is_published: bool = Field(default=True, description="Whether connector is published")
    created_by: Optional[str] = Field(None, description="User who created the connector")

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

    @validator('color')
    def validate_color_format(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be in hex format (e.g., #8b5cf6)')
        if v and len(v) != 7:
            raise ValueError('Color must be 7 characters long including # (e.g., #8b5cf6)')
        return v

    class Config:
        allow_population_by_field_name = True

class VerticalConnectorResponse(BaseModel):
    connector_id: str
    name: str
    shared_id: str
    connector_type: str
    floor_id: str
    shape: str
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None
    color: str
    is_published: bool
    created_by: Optional[str] = None
    datetime: float
    updated_by: Optional[str] = None
    update_on: Optional[float] = None
    status: str
    metadata: Optional[dict] = None

    class Config:
        allow_population_by_field_name = True

async def main(connector_data: VerticalConnectorCreateRequest):
    try:
        # Validate shape-specific requirements
        if connector_data.shape == ShapeType.RECTANGLE:
            if not connector_data.width or not connector_data.height:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Width and height are required for rectangle shape"
                )
        elif connector_data.shape == ShapeType.CIRCLE:
            if not connector_data.radius:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Radius is required for circle shape"
                )

        # Check if floor exists
        floor = await Floor.find_one({
            "floor_id": connector_data.floor_id,
            "status": "active"
        })
        
        if not floor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Floor with ID '{connector_data.floor_id}' not found"
            )

        # Check if connector with same name exists on the same floor
        existing_connector = await VerticalConnector.find_one({
            "name": connector_data.name,
            "floor_id": connector_data.floor_id,
            "status": "active"
        })
        
        if existing_connector:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Vertical connector with name '{connector_data.name}' already exists on this floor"
            )

        # Create new vertical connector
        new_connector = VerticalConnector(
            name=connector_data.name,
            shared_id=connector_data.shared_id,
            connector_type=connector_data.connector_type,
            floor_id=connector_data.floor_id,
            shape=connector_data.shape,
            x=connector_data.x,
            y=connector_data.y,
            width=connector_data.width,
            height=connector_data.height,
            radius=connector_data.radius,
            color=connector_data.color,
            is_published=connector_data.is_published,
            created_by=connector_data.created_by,
            datetime=time.time(),
            status="active"
        )

        # Save to database
        await new_connector.insert()
        
        # Update floor's vertical_connectors list
        if new_connector.connector_id not in floor.vertical_connectors:
            floor.vertical_connectors.append(new_connector.connector_id)
            floor.updated_by = connector_data.created_by
            floor.update_on = time.time()
            await floor.save()
        
        logger.info(f"Vertical connector created successfully: {new_connector.connector_id} on floor: {connector_data.floor_id}")

        # Prepare response
        response = VerticalConnectorResponse(
            connector_id=new_connector.connector_id,
            name=new_connector.name,
            shared_id=new_connector.shared_id,
            connector_type=new_connector.connector_type.value,
            floor_id=new_connector.floor_id,
            shape=new_connector.shape.value,
            x=new_connector.x,
            y=new_connector.y,
            width=new_connector.width,
            height=new_connector.height,
            radius=new_connector.radius,
            color=new_connector.color,
            is_published=new_connector.is_published,
            created_by=new_connector.created_by,
            datetime=new_connector.datetime,
            updated_by=new_connector.updated_by,
            update_on=new_connector.update_on,
            status=new_connector.status,
            metadata=new_connector.metadata
        )

        return {
            "status": "success",
            "message": "Vertical connector created successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating vertical connector: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create vertical connector: {str(e)}"
        )
