from fastapi import HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from src.datamodel.database.domain.DigitalSignage import VerticalConnector, ConnectorType
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Vertical Connector"],
        "summary": "Get Vertical Connectors",
        "response_model": dict,
        "description": "Get vertical connectors with optional filtering by floor, building, or connector type.",
        "response_description": "List of vertical connectors",
        "deprecated": False,
    }
    return ApiConfig(**config)

class VerticalConnectorListItem(BaseModel):
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
    status: str

    class Config:
        allow_population_by_field_name = True

async def main(
    floor_id: Optional[str] = Query(None, description="Filter by floor ID"),
    connector_type: Optional[ConnectorType] = Query(None, description="Filter by connector type"),
    shared_id: Optional[str] = Query(None, description="Filter by shared ID"),
    is_published: Optional[bool] = Query(None, description="Filter by published status"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip")
):
    try:
        # Build filter query
        filter_query = {"status": "active"}
        
        if floor_id:
            filter_query["floor_id"] = floor_id
        
        if connector_type:
            filter_query["connector_type"] = connector_type
            
        if shared_id:
            filter_query["shared_id"] = shared_id
            
        if is_published is not None:
            filter_query["is_published"] = is_published

        # Get connectors with pagination
        connectors = await VerticalConnector.find(filter_query).skip(skip).limit(limit).to_list()
        
        # Get total count
        total_count = await VerticalConnector.find(filter_query).count()

        # Prepare response
        connector_list = [
            VerticalConnectorListItem(
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
                status=connector.status
            )
            for connector in connectors
        ]

        return {
            "status": "success",
            "message": f"Retrieved {len(connector_list)} vertical connectors",
            "data": {
                "connectors": connector_list,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "skip": skip,
                    "has_more": skip + len(connector_list) < total_count
                }
            }
        }

    except Exception as e:
        logger.exception(f"Error retrieving vertical connectors: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve vertical connectors: {str(e)}"
        )
