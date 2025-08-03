from fastapi import HTTPException, Query, status, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from src.datamodel.database.domain.DigitalSignage import Building
from src.datamodel.datavalidation.apiconfig import ApiConfig
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db
import time


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Building"],
        "summary": "Get Buildings",
        "response_model": dict,
        "description": "Retrieve all buildings or filter by specific criteria.",
        "response_description": "List of buildings",
        "deprecated": False,
    }
    return ApiConfig(**config)


class BuildingResponse(BaseModel):
    building_id: str
    name: str
    address: Optional[str] = None
    floors: List[str] = []
    description: Optional[str] = None
    entity_uuid: Optional[str] = None
    datetime: float
    updated_by: Optional[str] = None
    update_on: Optional[float] = None
    status: str

    class Config:
        allow_population_by_field_name = True


async def main(
    request: Request,
    status_filter: Optional[str] = Query("active", description="Filter by status (active, inactive, all)"),
    name: Optional[str] = Query(None, description="Filter by building name (partial match)"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    skip: Optional[int] = Query(0, description="Skip number of results for pagination"),
    db: AsyncSession = Depends(db)
):
    
    """Main handler for content uploads"""
    # Validate token and get user info
    validate_token_start = time.time()
    validate_token(request)
    entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    try:
        # Build query filter
        query_filter = {"entity_uuid": entity_uuid}
        
        if status_filter and status_filter != "all":
            query_filter["status"] = status_filter
        
        if name:
            query_filter["name"] = {"$regex": name, "$options": "i"}  # Case-insensitive partial match

        # Execute query
        query = Building.find(query_filter)
        
        if skip:
            query = query.skip(skip)
        if limit:
            query = query.limit(limit)
            
        buildings = await query.to_list()
        
        # Prepare response
        building_list = []
        for building in buildings:
            building_response = BuildingResponse(
                building_id=building.building_id,
                name=building.name,
                address=building.address,
                floors=building.floors or [],
                description=building.description,
                entity_uuid=building.entity_uuid,
                datetime=building.datetime,
                updated_by=building.updated_by,
                update_on=building.update_on,
                status=building.status
            )
            building_list.append(building_response)

        logger.info(f"Retrieved {len(building_list)} buildings")

        return {
            "status": "success",
            "message": f"Retrieved {len(building_list)} buildings",
            "data": building_list,
            "total": len(building_list)
        }

    except Exception as e:
        logger.exception(f"Error retrieving buildings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve buildings: {str(e)}"
        )
