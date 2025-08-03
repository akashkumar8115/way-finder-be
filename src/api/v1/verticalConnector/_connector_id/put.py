from fastapi import HTTPException, Path as FastAPIPath, status
from pydantic import BaseModel, Field, validator
from typing import Optional
import time
import logging
from src.datamodel.database.domain.DigitalSignage import VerticalConnector, ShapeType, ConnectorType
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Vertical Connector"],
        "summary": "Update Vertical Connector",
        "response_model": dict,
        "description": "Update an existing vertical connector.",
        "response_description": "Updated vertical connector data",
        "deprecated": False,
    }
    return ApiConfig(**config)

class VerticalConnectorUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Name of the connector")
    shared_id: Optional[str] = Field(None, description="Shared identifier across floors")
    connector_type: Optional[ConnectorType] = Field(None, description="Type of vertical connector")
    shape: Optional[ShapeType] = Field(None, description="Shape type - circle or rectangle")
    x: Optional[float] = Field(None, description="X coordinate position")
    y: Optional[float] = Field(None, description="Y coordinate position")
    width: Optional[float] = Field(None, description="Width for rectangle shape")
    height: Optional[float] = Field(None, description="Height for rectangle shape")
    radius: Optional[float] = Field(None, description="Radius for circle shape")
    color: Optional[str] = Field(None, description="Color for connector display")
    is_published: Optional[bool] = Field(None, description="Whether connector is published")
    updated_by: Optional[str] = Field(None, description="User who updated the connector")

    @validator('color')
    def validate_color_format(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be in hex format (e.g., #8b5cf6)')
        if v and len(v) != 7:
            raise ValueError('Color must be 7 characters long including # (e.g., #8b5cf6)')
        return v

    class Config:
        allow_population_by_field_name = True

class VerticalConnectorUpdateResponse(BaseModel):
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

async def main(
    connector_id: str = FastAPIPath(..., description="Vertical connector ID to update"),
    connector_data: VerticalConnectorUpdateRequest = None
):
    try:
        # Find the existing connector
        existing_connector = await VerticalConnector.find_one({
            "connector_id": connector_id,
            "status": "active"
        })
        
        if not existing_connector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vertical connector with ID '{connector_id}' not found"
            )

        # Validate shape-specific requirements if shape is being updated
        if connector_data.shape:
            if connector_data.shape == ShapeType.RECTANGLE:
                width = connector_data.width if connector_data.width is not None else existing_connector.width
                height = connector_data.height if connector_data.height is not None else existing_connector.height
                if not width or not height:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Width and height are required for rectangle shape"
                    )
            elif connector_data.shape == ShapeType.CIRCLE:
                radius = connector_data.radius if connector_data.radius is not None else existing_connector.radius
                if not radius:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Radius is required for circle shape"
                    )

        # Check if updated name conflicts with existing connectors on the same floor
        if connector_data.name and connector_data.name != existing_connector.name:
            name_conflict = await VerticalConnector.find_one({
                "name": connector_data.name,
                "floor_id": existing_connector.floor_id,
                "connector_id": {"$ne": connector_id},
                "status": "active"
            })
            
            if name_conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Vertical connector with name '{connector_data.name}' already exists on this floor"
                )

        # Update fields
        update_data = {}
        
        if connector_data.name is not None:
            update_data["name"] = connector_data.name
        if connector_data.shared_id is not None:
            update_data["shared_id"] = connector_data.shared_id
        if connector_data.connector_type is not None:
            update_data["connector_type"] = connector_data.connector_type
        if connector_data.shape is not None:
            update_data["shape"] = connector_data.shape
        if connector_data.x is not None:
            update_data["x"] = connector_data.x
        if connector_data.y is not None:
            update_data["y"] = connector_data.y
        if connector_data.width is not None:
            update_data["width"] = connector_data.width
        if connector_data.height is not None:
            update_data["height"] = connector_data.height
        if connector_data.radius is not None:
            update_data["radius"] = connector_data.radius
        if connector_data.color is not None:
            update_data["color"] = connector_data.color
        if connector_data.is_published is not None:
            update_data["is_published"] = connector_data.is_published
        if connector_data.updated_by is not None:
            update_data["updated_by"] = connector_data.updated_by
        
        update_data["update_on"] = time.time()

        # Update the connector
        for key, value in update_data.items():
            setattr(existing_connector, key, value)
        
        await existing_connector.save()
        
        logger.info(f"Vertical connector updated successfully: {connector_id}")

        # Prepare response
        response = VerticalConnectorUpdateResponse(
            connector_id=existing_connector.connector_id,
            name=existing_connector.name,
            shared_id=existing_connector.shared_id,
            connector_type=existing_connector.connector_type.value,
            floor_id=existing_connector.floor_id,
            shape=existing_connector.shape.value,
            x=existing_connector.x,
            y=existing_connector.y,
            width=existing_connector.width,
            height=existing_connector.height,
            radius=existing_connector.radius,
            color=existing_connector.color,
            is_published=existing_connector.is_published,
            created_by=existing_connector.created_by,
            datetime=existing_connector.datetime,
            updated_by=existing_connector.updated_by,
            update_on=existing_connector.update_on,
            status=existing_connector.status,
            metadata=existing_connector.metadata
        )

        return {
            "status": "success",
            "message": "Vertical connector updated successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating vertical connector: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update vertical connector: {str(e)}"
        )
