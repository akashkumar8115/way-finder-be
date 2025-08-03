from fastapi import HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
from src.datamodel.database.domain.DigitalSignage import VerticalConnector, Floor
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Vertical Connector"],
        "summary": "Get Vertical Connectors by Floor ID",
        "response_model": dict,
        "description": "Retrieve all vertical connectors for a specific floor.",
        "response_description": "List of vertical connectors for the specified floor",
        "deprecated": False,
    }
    return ApiConfig(**config)

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

async def main(floor_id: str):
    try:
        # Check if floor exists
        floor = await Floor.find_one({
            "floor_id": floor_id,
            "status": "active"
        })
        
        if not floor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Floor with ID '{floor_id}' not found"
            )

        # Get all vertical connectors for the specified floor
        connectors = await VerticalConnector.find({
            "floor_id": floor_id,
            "status": "active"
        }).to_list()

        # Convert to response format
        connector_responses = []
        for connector in connectors:
            response = VerticalConnectorResponse(
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
            connector_responses.append(response)

        logger.info(f"Retrieved {len(connector_responses)} vertical connectors for floor: {floor_id}")

        return {
            "status": "success",
            "message": f"Retrieved vertical connectors for floor '{floor_id}'",
            "data": {
                "floor_id": floor_id,
                "total_connectors": len(connector_responses),
                "connectors": connector_responses
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving vertical connectors for floor {floor_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve vertical connectors: {str(e)}"
        )
