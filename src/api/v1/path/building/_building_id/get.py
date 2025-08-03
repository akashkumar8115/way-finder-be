from fastapi import HTTPException, Path as FastAPIPath, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from src.datamodel.database.domain.DigitalSignage import Path, Building
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Path"],
        "summary": "Get Paths by Building ID",
        "response_model": dict,
        "description": "Get all navigation paths associated with a specific building. Returns both single-floor and multi-floor paths.",
        "response_description": "List of paths in the building",
        "deprecated": False,
    }
    return ApiConfig(**config)

class PathSummaryResponse(BaseModel):
    path_id: str
    name: str
    is_multi_floor: bool
    building_id: Optional[str] = None
    floor_id: Optional[str] = None
    source: str
    destination: str
    source_tag_id: Optional[str] = None
    destination_tag_id: Optional[str] = None
    
    # Multi-floor specific fields
    total_floors: Optional[int] = None
    source_floor_id: Optional[str] = None
    destination_floor_id: Optional[str] = None
    floors_involved: Optional[List[str]] = None
    
    # Common fields
    shape: str
    color: str
    is_published: bool
    created_by: Optional[str] = None
    datetime: float
    updated_by: Optional[str] = None
    update_on: Optional[float] = None
    status: str
    estimated_time: Optional[int] = None

    class Config:
        allow_population_by_field_name = True

class BuildingPathsResponse(BaseModel):
    building_id: str
    building_name: Optional[str] = None
    total_paths: int
    single_floor_paths: int
    multi_floor_paths: int
    paths: List[PathSummaryResponse]

    class Config:
        allow_population_by_field_name = True

async def main(
    building_id: str = FastAPIPath(..., description="Building ID to get paths for"),
    is_published: Optional[bool] = Query(None, description="Filter by published status"),
    path_type: Optional[str] = Query(None, description="Filter by path type: 'single' or 'multi'"),
    limit: Optional[int] = Query(None, description="Limit number of results", ge=1, le=100),
    skip: Optional[int] = Query(0, description="Number of results to skip", ge=0)
):
    try:
        # Validate building exists
        building = await Building.find_one({
            "building_id": building_id,
            "status": "active"
        })
        
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building with ID '{building_id}' not found"
            )

        # Build query filters
        query_filters = {
            "status": "active"
        }

        # Add building filter - for multi-floor paths, use building_id directly
        # For single-floor paths, we need to find floors in this building first
        building_query = {
            "$or": [
                {"building_id": building_id},  # Multi-floor paths
                {"floor_id": {"$in": []}}      # Single-floor paths (will be populated below)
            ]
        }

        # Get all floors in this building for single-floor path filtering
        from src.datamodel.database.domain.DigitalSignage import Floor
        floors_in_building = await Floor.find({
            "building_id": building_id,
            "status": "active"
        }).to_list()
        
        floor_ids = [floor.floor_id for floor in floors_in_building]
        building_query["$or"][1]["floor_id"]["$in"] = floor_ids

        query_filters.update(building_query)

        # Add optional filters
        if is_published is not None:
            query_filters["is_published"] = is_published

        if path_type:
            if path_type.lower() == "single":
                query_filters["is_multi_floor"] = False
            elif path_type.lower() == "multi":
                query_filters["is_multi_floor"] = True
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="path_type must be either 'single' or 'multi'"
                )

        # Execute query with pagination
        query = Path.find(query_filters)
        
        if skip:
            query = query.skip(skip)
        if limit:
            query = query.limit(limit)

        paths = await query.to_list()

        # Count totals for summary
        total_paths = len(paths)
        single_floor_count = sum(1 for path in paths if not getattr(path, 'is_multi_floor', False))
        multi_floor_count = total_paths - single_floor_count

        # Prepare path responses
        path_responses = []
        for path in paths:
            # Extract estimated_time from metadata
            estimated_time = None
            if hasattr(path, 'metadata') and path.metadata:
                estimated_time = path.metadata.get('estimated_time')

            # Get floors involved for multi-floor paths
            floors_involved = None
            if getattr(path, 'is_multi_floor', False) and hasattr(path, 'metadata') and path.metadata:
                floors_involved = path.metadata.get('floors_involved', [])

            path_response = PathSummaryResponse(
                path_id=path.path_id,
                name=path.name,
                is_multi_floor=getattr(path, 'is_multi_floor', False),
                building_id=getattr(path, 'building_id', None),
                floor_id=getattr(path, 'floor_id', None),
                source=path.source,
                destination=path.destination,
                source_tag_id=path.source_tag_id,
                destination_tag_id=path.destination_tag_id,
                total_floors=getattr(path, 'total_floors', None),
                source_floor_id=getattr(path, 'source_floor_id', None),
                destination_floor_id=getattr(path, 'destination_floor_id', None),
                floors_involved=floors_involved,
                shape=path.shape.value,
                color=path.color,
                is_published=path.is_published,
                created_by=path.created_by,
                datetime=path.datetime,
                updated_by=path.updated_by,
                update_on=path.update_on,
                status=path.status,
                estimated_time=estimated_time
            )
            path_responses.append(path_response)

        # Sort paths by creation date (newest first)
        path_responses.sort(key=lambda x: x.datetime, reverse=True)

        # Prepare final response
        response = BuildingPathsResponse(
            building_id=building_id,
            building_name=getattr(building, 'name', None),
            total_paths=total_paths,
            single_floor_paths=single_floor_count,
            multi_floor_paths=multi_floor_count,
            paths=path_responses
        )

        logger.info(f"Retrieved {total_paths} paths for building: {building_id}")

        return {
            "status": "success",
            "message": f"Retrieved {total_paths} paths for building '{building_id}'",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving paths for building: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve paths for building: {str(e)}"
        )
