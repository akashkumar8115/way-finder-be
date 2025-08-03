from fastapi import HTTPException, Path as FastAPIPath, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from src.datamodel.database.domain.DigitalSignage import VerticalConnector
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Vertical Connector"],
        "summary": "Get Connectors by Shared ID",
        "response_model": dict,
        "description": "Get all vertical connectors that share the same shared_id across different floors (e.g., same elevator on different floors).",
        "response_description": "List of connectors with same shared ID",
        "deprecated": False,
    }
    return ApiConfig(**config)

class ConnectorBySharedIdItem(BaseModel):
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

class ConnectorGroupResponse(BaseModel):
    shared_id: str
    connector_type: str
    total_floors: int
    connectors: List[ConnectorBySharedIdItem]
    floor_ids: List[str]

    class Config:
        allow_population_by_field_name = True

async def main(
    shared_id: str = FastAPIPath(..., description="Shared ID to search for"),
    building_id: Optional[str] = Query(None, description="Filter by building ID"),
    is_published: Optional[bool] = Query(None, description="Filter by published status"),
    include_inactive: bool = Query(False, description="Include inactive connectors")
):
    try:
        # Build filter query
        filter_query = {"shared_id": shared_id}
        
        if not include_inactive:
            filter_query["status"] = "active"
        
        if is_published is not None:
            filter_query["is_published"] = is_published

        # Get connectors with the shared ID
        connectors = await VerticalConnector.find(filter_query).to_list()
        
        if not connectors:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No vertical connectors found with shared ID '{shared_id}'"
            )

        # Filter by building if specified
        if building_id:
            # We need to get floor information to filter by building
            from src.datamodel.database.domain.DigitalSignage import Floor
            
            # Get all floors for the building
            building_floors = await Floor.find({
                "building_id": building_id,
                "status": "active"
            }).to_list()
            
            building_floor_ids = [floor.floor_id for floor in building_floors]
            
            # Filter connectors to only those on floors in the specified building
            connectors = [conn for conn in connectors if conn.floor_id in building_floor_ids]
            
            if not connectors:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No vertical connectors found with shared ID '{shared_id}' in building '{building_id}'"
                )

        # Sort connectors by floor_id for consistent ordering
        connectors.sort(key=lambda x: x.floor_id)

        # Prepare connector list
        connector_list = [
            ConnectorBySharedIdItem(
                connector_id=conn.connector_id,
                name=conn.name,
                shared_id=conn.shared_id,
                connector_type=conn.connector_type.value,
                floor_id=conn.floor_id,
                shape=conn.shape.value,
                x=conn.x,
                y=conn.y,
                width=conn.width,
                height=conn.height,
                radius=conn.radius,
                color=conn.color,
                is_published=conn.is_published,
                created_by=conn.created_by,
                datetime=conn.datetime,
                status=conn.status
            )
            for conn in connectors
        ]

        # Get unique floor IDs
        floor_ids = list(set([conn.floor_id for conn in connectors]))
        floor_ids.sort()

        # Get connector type (should be same for all connectors with same shared_id)
        connector_type = connectors[0].connector_type.value

        # Prepare response
        response = ConnectorGroupResponse(
            shared_id=shared_id,
            connector_type=connector_type,
            total_floors=len(floor_ids),
            connectors=connector_list,
            floor_ids=floor_ids
        )

        logger.info(f"Retrieved {len(connectors)} connectors with shared ID '{shared_id}'")

        return {
            "status": "success",
            "message": f"Retrieved {len(connectors)} connectors with shared ID '{shared_id}'",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving connectors by shared ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve connectors by shared ID: {str(e)}"
        )
