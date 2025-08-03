from fastapi import HTTPException, Path as FastAPIPath, status
from pydantic import BaseModel, Field
from typing import Optional
import logging
from src.datamodel.database.domain.DigitalSignage import VerticalConnector
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Vertical Connector"],
        "summary": "Get Vertical Connector by ID",
        "response_model": dict,
        "description": "Get a specific vertical connector by its ID.",
        "response_description": "Vertical connector details",
        "deprecated": False,
    }
    return ApiConfig(**config)

class VerticalConnectorDetailResponse(BaseModel):
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
    connector_id: str = FastAPIPath(..., description="Vertical connector ID to retrieve")
):
    try:
        # Find the connector by ID
        connector = await VerticalConnector.find_one({
            "connector_id": connector_id,
            "status": "active"
        })
        
        if not connector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vertical connector with ID '{connector_id}' not found"
            )

        # Prepare response
        response = VerticalConnectorDetailResponse(
            connector_id=connector.connector_id,
            name=connector.name,
            shared_id=connector.shared_id,
            connector_type=connector.connector_type.value,
            floor_id=connector.floor_id,
            shape=connector.shape.value,
            x=connector.x,
            y=connector.y,
            width=connector.width,
            height=connector.height,
            radius=connector.radius,
            color=connector.color,
            is_published=connector.is_published,
            created_by=connector.created_by,
            datetime=connector.datetime,
            updated_by=connector.updated_by,
            update_on=connector.update_on,
            status=connector.status,
            metadata=connector.metadata
        )

        return {
            "status": "success",
            "message": "Vertical connector retrieved successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving vertical connector: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve vertical connector: {str(e)}"
        )
