from fastapi import HTTPException, Path, Query, status, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from src.datamodel.database.domain.DigitalSignage import Building, Floor
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db
import time
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Floor"],
        "summary": "Get Floors by Building ID",
        "response_model": dict,
        "description": "Retrieve all floors for a specific building.",
        "response_description": "List of floors for the building",
        "deprecated": False,
    }
    return ApiConfig(**config)


class FloorResponse(BaseModel):
    floor_id: str
    name: str
    building_id: str
    floor_number: int
    floor_plan_url: Optional[str] = None
    locations_count: int
    description: Optional[str] = None
    entity_uuid: Optional[str] = None
    datetime: float
    updated_by: Optional[str] = None
    update_on: Optional[float] = None
    status: str

    class Config:
        allow_population_by_field_name = True


class BuildingFloorsResponse(BaseModel):
    building_id: str
    building_name: str
    total_floors: int
    floors: List[FloorResponse]

    class Config:
        allow_population_by_field_name = True


async def main(
    request: Request,
    building_id: str = Path(..., description="Building ID to get floors for"),
    status_filter: Optional[str] = Query("active", description="Filter by status (active, inactive, all)"),
    include_locations_count: Optional[bool] = Query(True, description="Include count of locations on each floor"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    skip: Optional[int] = Query(0, description="Skip number of results for pagination"),
    db: AsyncSession = Depends(db)
):
    
        # Get entity_uuid from request
    validate_token_start = time.time()
    
    validate_token(request)
    # await verify_permissions(request, "content", "read")

    entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")



    try:
        # First, verify that the building exists
        building = await Building.find_one({
            "building_id": building_id,
            "entity_uuid": entity_uuid
        })
        
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building with ID '{building_id}' not found"
            )

        # Build query filter for floors
        query_filter = {"building_id": building_id}
        
        if status_filter and status_filter != "all":
            query_filter["status"] = status_filter

        # Execute query to get floors
        query = Floor.find(query_filter).sort("floor_number")  # Sort by floor number
        
        if skip:
            query = query.skip(skip)
        if limit:
            query = query.limit(limit)
            
        floors = await query.to_list()
        
        # Prepare response
        floor_list = []
        for floor in floors:
            locations_count = 0
            if include_locations_count and floor.locations:
                locations_count = len(floor.locations)
            
            floor_response = FloorResponse(
                floor_id=floor.floor_id,
                name=floor.name,
                building_id=floor.building_id,
                floor_number=floor.floor_number,
                floor_plan_url=floor.floor_plan_url,
                locations_count=locations_count,
                description=floor.description,
                entity_uuid=floor.entity_uuid,
                datetime=floor.datetime,
                updated_by=floor.updated_by,
                update_on=floor.update_on,
                status=floor.status
            )
            floor_list.append(floor_response)

        # Create comprehensive response
        response = BuildingFloorsResponse(
            building_id=building.building_id,
            building_name=building.name,
            total_floors=len(floor_list),
            floors=floor_list
        )

        logger.info(f"Retrieved {len(floor_list)} floors for building: {building_id}")

        return {
            "status": "success",
            "message": f"Retrieved {len(floor_list)} floors for building '{building.name}'",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving floors for building {building_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve floors for building: {str(e)}"
        )
