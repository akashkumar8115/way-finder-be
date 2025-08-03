
from fastapi import HTTPException, Depends, status
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
import time
import logging
from src.datamodel.database.domain.DigitalSignage import (
    Path, PathPoint, ShapeType, Floor, Location, VerticalConnector, 
    ConnectorType, Building
)
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 201,
        "tags": ["Path"],
        "summary": "Create Path (Single or Multi-Floor)",
        "response_model": dict,
        "description": "Create a navigation path between locations. Supports both single-floor and multi-floor paths with vertical connectors.",
        "response_description": "Created path data",
        "deprecated": False,
    }
    return ApiConfig(**config)

class PathPointRequest(BaseModel):
    x: float = Field(..., description="X coordinate of path point")
    y: float = Field(..., description="Y coordinate of path point")

class FloorSegmentRequest(BaseModel):
    floor_id: str = Field(..., description="Floor ID for this segment")
    points: List[PathPointRequest] = Field(..., description="Path points for this floor", min_items=2)
    entry_connector_id: Optional[str] = Field(None, description="Vertical connector used to enter this floor")
    exit_connector_id: Optional[str] = Field(None, description="Vertical connector used to exit this floor")

class VerticalTransitionRequest(BaseModel):
    from_floor_id: str = Field(..., description="Source floor ID")
    to_floor_id: str = Field(..., description="Destination floor ID")
    connector_id: str = Field(..., description="Vertical connector ID used for transition")
    connector_type: ConnectorType = Field(..., description="Type of vertical connector")
    instruction: Optional[str] = Field(None, description="Navigation instruction for this transition")

class PathCreateRequest(BaseModel):
    name: str = Field(..., description="Name of the path")
    
    # Multi-floor support fields
    is_multi_floor: bool = Field(default=False, description="Whether this is a multi-floor path")
    building_id: Optional[str] = Field(None, description="Building ID (required for multi-floor paths)")
    
    # Single-floor fields (used when is_multi_floor=False)
    floor_id: Optional[str] = Field(None, description="ID of the floor this path belongs to (for single-floor paths)")
    points: Optional[List[PathPointRequest]] = Field(None, description="Array of path points (for single-floor paths)")
    
    # Multi-floor fields (used when is_multi_floor=True)
    floor_segments: Optional[List[FloorSegmentRequest]] = Field(None, description="Path segments for each floor (multi-floor only)")
    vertical_transitions: Optional[List[VerticalTransitionRequest]] = Field(None, description="Vertical transitions between floors (multi-floor only)")
    
    # Common fields for both types
    source: str = Field(..., description="Source location/connector name")
    destination: str = Field(..., description="Destination location/connector name")
    source_tag_id: Optional[str] = Field(None, description="Source location/connector ID")
    destination_tag_id: Optional[str] = Field(None, description="Destination location/connector ID")
    
    # Path styling
    shape: ShapeType = Field(..., description="Shape type for path visualization")
    width: Optional[float] = Field(None, description="Width for rectangle shape")
    height: Optional[float] = Field(None, description="Height for rectangle shape")
    radius: Optional[float] = Field(None, description="Radius for circle shape")
    color: str = Field(..., description="Color for path display")
    
    # Metadata
    is_published: bool = Field(default=True, description="Whether path is published")
    created_by: Optional[str] = Field(None, description="User who created the path")
    estimated_time: Optional[int] = Field(None, description="Estimated time in minutes")

    @validator('building_id')
    def validate_building_id(cls, v, values):
        if values.get('is_multi_floor') and not v:
            raise ValueError('Building ID is required for multi-floor paths')
        return v

    @validator('floor_id')
    def validate_floor_id(cls, v, values):
        if not values.get('is_multi_floor') and not v:
            raise ValueError('Floor ID is required for single-floor paths')
        return v

    @validator('points')
    def validate_points(cls, v, values):
        if not values.get('is_multi_floor'):
            if not v or len(v) < 2:
                raise ValueError('Single-floor path must have at least 2 points')
        return v

    @validator('floor_segments')
    def validate_floor_segments(cls, v, values):
        if values.get('is_multi_floor'):
            if not v or len(v) < 2:
                raise ValueError('Multi-floor path must have at least 2 floor segments')
            
            # Check that each segment has at least 2 points
            for segment in v:
                if len(segment.points) < 2:
                    raise ValueError('Each floor segment must have at least 2 points')
        return v

    @validator('vertical_transitions')
    def validate_transitions(cls, v, values):
        if values.get('is_multi_floor'):
            floor_segments = values.get('floor_segments', [])
            if not v or len(v) != len(floor_segments) - 1:
                raise ValueError('Number of vertical transitions must be one less than floor segments')
        return v

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
            raise ValueError('Color must be in hex format (e.g., #3b82f6)')
        if v and len(v) != 7:
            raise ValueError('Color must be 7 characters long including # (e.g., #3b82f6)')
        return v

    class Config:
        allow_population_by_field_name = True

class PathResponse(BaseModel):
    path_id: str
    name: str
    is_multi_floor: bool
    building_id: Optional[str] = None
    floor_id: Optional[str] = None
    source: str
    destination: str
    source_tag_id: Optional[str] = None
    destination_tag_id: Optional[str] = None
    
    # Single-floor fields
    points: Optional[List[dict]] = None
    
    # Multi-floor fields
    floor_segments: Optional[List[dict]] = None
    vertical_transitions: Optional[List[dict]] = None
    total_floors: Optional[int] = None
    source_floor_id: Optional[str] = None
    destination_floor_id: Optional[str] = None
    
    # Common fields
    shape: str
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
    estimated_time: Optional[int] = None
    metadata: Optional[dict] = None

    class Config:
        allow_population_by_field_name = True

async def main(path_data: PathCreateRequest):
    try:
        if path_data.is_multi_floor:
            return await _create_multi_floor_path(path_data)
        else:
            return await _create_single_floor_path(path_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating path: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create path: {str(e)}"
        )

async def _create_single_floor_path(path_data: PathCreateRequest):
    """Create a single-floor path (existing logic)"""
    
    # Check if floor exists
    floor = await Floor.find_one({
        "floor_id": path_data.floor_id,
        "status": "active"
    })
    
    if not floor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Floor with ID '{path_data.floor_id}' not found"
        )

    # Validate source and destination IDs if provided
    if path_data.source_tag_id:
        source_exists = await _validate_tag_exists(path_data.source_tag_id, path_data.floor_id)
        if not source_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source location/connector with ID '{path_data.source_tag_id}' not found on this floor"
            )

    if path_data.destination_tag_id:
        dest_exists = await _validate_tag_exists(path_data.destination_tag_id, path_data.floor_id)
        if not dest_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Destination location/connector with ID '{path_data.destination_tag_id}' not found on this floor"
            )

    # Check if path with same name exists on the same floor
    existing_path = await Path.find_one({
        "name": path_data.name,
        "floor_id": path_data.floor_id,
        "is_multi_floor": False,
        "status": "active"
    })
    
    # if existing_path:
    #     raise HTTPException(
    #         status_code=status.HTTP_409_CONFLICT,
    #         detail=f"Path with name '{path_data.name}' already exists on this floor"
    #     )

    # Convert PathPointRequest to PathPoint
    path_points = [PathPoint(x=point.x, y=point.y) for point in path_data.points]

    # Create new single-floor path
    new_path = Path(
        name=path_data.name,
        is_multi_floor=False,
        floor_id=path_data.floor_id,
        source=path_data.source,
        destination=path_data.destination,
        source_tag_id=path_data.source_tag_id,
        destination_tag_id=path_data.destination_tag_id,
        points=path_points,
        shape=path_data.shape,
        width=path_data.width,
        height=path_data.height,
        radius=path_data.radius,
        color=path_data.color,
        is_published=path_data.is_published,
        created_by=path_data.created_by,
        datetime=time.time(),
        status="active",
        metadata={"estimated_time": path_data.estimated_time} if path_data.estimated_time else {}
    )

    # Save to database
    await new_path.insert()
    
    # Update floor's paths list
    if new_path.path_id not in floor.paths:
        floor.paths.append(new_path.path_id)
        floor.updated_by = path_data.created_by
        floor.update_on = time.time()
        await floor.save()
    
    logger.info(f"Single-floor path created successfully: {new_path.path_id} on floor: {path_data.floor_id}")

    # Prepare response
    response = PathResponse(
        path_id=new_path.path_id,
        name=new_path.name,
        is_multi_floor=False,
        floor_id=new_path.floor_id,
        source=new_path.source,
        destination=new_path.destination,
        source_tag_id=new_path.source_tag_id,
        destination_tag_id=new_path.destination_tag_id,
        points=[{"x": point.x, "y": point.y} for point in new_path.points],
        shape=new_path.shape.value,
        width=new_path.width,
        height=new_path.height,
        radius=new_path.radius,
        color=new_path.color,
        is_published=new_path.is_published,
        created_by=new_path.created_by,
        datetime=new_path.datetime,
        updated_by=new_path.updated_by,
        update_on=new_path.update_on,
        status=new_path.status,
        estimated_time=path_data.estimated_time,
        metadata=new_path.metadata
    )

    return {
        "status": "success",
        "message": "Single-floor path created successfully",
        "data": response
    }



async def _create_multi_floor_path(path_data: PathCreateRequest):
    """Create a multi-floor path"""
    
    # Validate building exists
    building = await Building.find_one({
        "building_id": path_data.building_id,
        "status": "active"
    })
    
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building with ID '{path_data.building_id}' not found"
        )

    # Validate source and destination locations exist
    source_location = await Location.find_one({
        "location_id": path_data.source_tag_id,
        "status": "active"
    }) if path_data.source_tag_id else None
    
    destination_location = await Location.find_one({
        "location_id": path_data.destination_tag_id,
        "status": "active"
    }) if path_data.destination_tag_id else None

    # Validate all floors exist and belong to the building
    floor_ids = [segment.floor_id for segment in path_data.floor_segments]
    floors = await Floor.find({"floor_id": {"$in": floor_ids}, "status": "active"}).to_list()
    
    if len(floors) != len(floor_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more floors not found"
        )
    
    # Validate floors belong to the building
    for floor in floors:
        if floor.building_id != path_data.building_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Floor '{floor.floor_id}' does not belong to building '{path_data.building_id}'"
            )

    # Validate vertical connectors exist
    for transition in path_data.vertical_transitions:
        connector = await VerticalConnector.find_one({
            "connector_id": transition.connector_id,
            "status": "active"
        })
        
        if not connector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vertical connector with ID '{transition.connector_id}' not found"
            )

    # Check if multi-floor path with same name exists in the building
    existing_path = await Path.find_one({
        "name": path_data.name,
        "building_id": path_data.building_id,
        "is_multi_floor": True,
        "status": "active"
    })
    
    if existing_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Multi-floor path with name '{path_data.name}' already exists in this building"
        )

    # Prepare floor segments data
    floor_segments_data = []
    for i, segment in enumerate(path_data.floor_segments):
        # Convert points
        segment_points = [{"x": point.x, "y": point.y} for point in segment.points]
        
        # Determine source and destination for this segment
        if i == 0:  # First segment
            segment_source = path_data.source
            segment_source_id = path_data.source_tag_id
        else:
            # Use the entry connector as source
            connector = await VerticalConnector.find_one({"connector_id": segment.entry_connector_id})
            segment_source = connector.name if connector else "Connector"
            segment_source_id = segment.entry_connector_id
        
        if i == len(path_data.floor_segments) - 1:  # Last segment
            segment_destination = path_data.destination
            segment_destination_id = path_data.destination_tag_id
        else:
            # Use the exit connector as destination
            connector = await VerticalConnector.find_one({"connector_id": segment.exit_connector_id})
            segment_destination = connector.name if connector else "Connector"
            segment_destination_id = segment.exit_connector_id
        
        floor_segments_data.append({
            "floor_id": segment.floor_id,
            "points": segment_points,
            "entry_connector_id": segment.entry_connector_id,
            "exit_connector_id": segment.exit_connector_id,
            "source": segment_source,
            "destination": segment_destination,
            "source_tag_id": segment_source_id,
            "destination_tag_id": segment_destination_id,
            "segment_index": i
        })

    # Prepare vertical transitions data
    vertical_transitions_data = []
    for transition in path_data.vertical_transitions:
        connector = await VerticalConnector.find_one({"connector_id": transition.connector_id})
        vertical_transitions_data.append({
            "from_floor_id": transition.from_floor_id,
            "to_floor_id": transition.to_floor_id,
            "connector_id": transition.connector_id,
            "connector_type": transition.connector_type.value,
            "connector_name": connector.name if connector else "Unknown",
            "instruction": transition.instruction or f"Take {transition.connector_type.value} to next floor"
        })

    # Get source and destination floor IDs
    source_floor_id = source_location.floor_id if source_location else path_data.floor_segments[0].floor_id
    destination_floor_id = destination_location.floor_id if destination_location else path_data.floor_segments[-1].floor_id

    # Create the multi-floor path record
    new_path = Path(
        name=path_data.name,
        is_multi_floor=True,
        building_id=path_data.building_id,
        source_floor_id=source_floor_id,
        destination_floor_id=destination_floor_id,
        source=path_data.source,
        destination=path_data.destination,
        source_tag_id=path_data.source_tag_id,
        destination_tag_id=path_data.destination_tag_id,
        points=[],  # Empty for multi-floor paths
        floor_segments=floor_segments_data,
        vertical_transitions=vertical_transitions_data,
        total_floors=len(path_data.floor_segments),
        shape=path_data.shape,
        width=path_data.width,
        height=path_data.height,
        radius=path_data.radius,
        color=path_data.color,
        is_published=path_data.is_published,
        created_by=path_data.created_by,
        datetime=time.time(),
        status="active",
        metadata={
            "estimated_time": path_data.estimated_time,
            "building_name": building.name,
            "source_location_name": source_location.name if source_location else path_data.source,
            "destination_location_name": destination_location.name if destination_location else path_data.destination,
            "floors_involved": floor_ids
        }
    )

    # Save to database
    await new_path.insert()
    
    # Update each floor's paths list
    for floor in floors:
        if new_path.path_id not in floor.paths:
            floor.paths.append(new_path.path_id)
            floor.updated_by = path_data.created_by
            floor.update_on = time.time()
            await floor.save()
    
    logger.info(f"Multi-floor path created successfully: {new_path.path_id} in building: {path_data.building_id}")

    # Prepare response
    response = PathResponse(
        path_id=new_path.path_id,
        name=new_path.name,
        is_multi_floor=True,
        building_id=new_path.building_id,
        source_floor_id=new_path.source_floor_id,
        destination_floor_id=new_path.destination_floor_id,
        source=new_path.source,
        destination=new_path.destination,
        source_tag_id=new_path.source_tag_id,
        destination_tag_id=new_path.destination_tag_id,
        floor_segments=new_path.floor_segments,
        vertical_transitions=new_path.vertical_transitions,
        total_floors=new_path.total_floors,
        shape=new_path.shape.value,
        width=new_path.width,
        height=new_path.height,
        radius=new_path.radius,
        color=new_path.color,
        is_published=new_path.is_published,
        created_by=new_path.created_by,
        datetime=new_path.datetime,
        updated_by=new_path.updated_by,
        update_on=new_path.update_on,
        status=new_path.status,
        estimated_time=path_data.estimated_time,
        metadata=new_path.metadata
    )

    return {
        "status": "success",
        "message": "Multi-floor path created successfully",
        "data": response
    }

async def _validate_tag_exists(tag_id: str, floor_id: str) -> bool:
    """
    Validate if a location or vertical connector exists on the specified floor
    """
    try:
        # Check if it's a location
        location = await Location.find_one({
            "location_id": tag_id,
            "floor_id": floor_id,
            "status": "active"
        })
        
        if location:
            return True
        
        # Check if it's a vertical connector
        connector = await VerticalConnector.find_one({
            "connector_id": tag_id,
            "floor_id": floor_id,
            "status": "active"
        })
        
        return connector is not None
        
    except Exception as e:
        logger.error(f"Error validating tag existence: {str(e)}")
        return False
                                   