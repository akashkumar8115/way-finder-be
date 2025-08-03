# from beanie import Document, Indexed
# from pydantic import Field, BaseModel
# from typing import Optional, Dict, List, Any
# from enum import Enum
# import time
# import uuid


# class ShapeType(str, Enum):
#     CIRCLE = "circle"
#     RECTANGLE = "rectangle"


# class Location(Document):
#     location_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the location")
#     name: Indexed(str) = Field(..., description="Name of the location")
#     floor_id: str = Field(..., description="ID of the floor this location belongs to")
#     category: str = Field(..., description="Category of the location")
#     shape: ShapeType = Field(..., description="Shape type - circle or rectangle")
#     x: float = Field(..., description="X coordinate position")
#     y: float = Field(..., description="Y coordinate position")
#     width: Optional[float] = Field(None, description="Width for rectangle shape")
#     height: Optional[float] = Field(None, description="Height for rectangle shape")
#     radius: Optional[float] = Field(None, description="Radius for circle shape")
#     logo_url: Optional[str] = Field(None, description="URL for location logo/icon")
#     created_by: Optional[str] = Field(None, description="User who created the location")
#     datetime: float = Field(default_factory=lambda: time.time(), description="Timestamp when location was created")
#     updated_by: Optional[str] = Field(None, description="User who last updated the location")
#     update_on: Optional[float] = Field(None, description="Timestamp of last update")
#     status: str = Field(default="active", description="Status of the location")
#     description: Optional[str] = Field(None, description="Description of the location")
#     metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

#     class Settings:
#         name = "locations"


# class Floor(Document):
#     floor_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the floor")
#     name: Indexed(str) = Field(..., description="Name of the floor")
#     building_id: Optional[str] = Field(None, description="Building identifier this floor belongs to")
#     floor_number: int = Field(..., description="Floor number")
#     floor_plan_url: Optional[str] = Field(None, description="URL to floor plan image")
#     locations: Optional[List[str]] = Field(default_factory=list, description="List of location IDs on this floor")
#     created_by: Optional[str] = Field(None, description="User who created the floor")
#     datetime: float = Field(default_factory=lambda: time.time(), description="Timestamp when floor was created")
#     updated_by: Optional[str] = Field(None, description="User who last updated the floor")
#     update_on: Optional[float] = Field(None, description="Timestamp of last update")
#     status: str = Field(default="active", description="Status of the floor")
#     description: Optional[str] = Field(None, description="Description of the floor")
#     metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

#     class Settings:
#         name = "floors"


# class Building(Document):
#     building_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the building")
#     name: Indexed(str) = Field(..., description="Name of the building")
#     address: Optional[str] = Field(None, description="Building address")
#     floors: Optional[List[str]] = Field(default_factory=list, description="List of floor IDs in this building")
#     created_by: Optional[str] = Field(None, description="User who created the building")
#     datetime: float = Field(default_factory=lambda: time.time(), description="Timestamp when building was created")
#     updated_by: Optional[str] = Field(None, description="User who last updated the building")
#     update_on: Optional[float] = Field(None, description="Timestamp of last update")
#     status: str = Field(default="active", description="Status of the building")
#     description: Optional[str] = Field(None, description="Description of the building")
#     metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

#     class Settings:
#         name = "buildings"








from beanie import Document, Indexed
from pydantic import Field, BaseModel
from typing import Optional, Dict, List, Any
from enum import Enum
import time
import uuid


class ShapeType(str, Enum):
    CIRCLE = "circle"
    RECTANGLE = "rectangle"


class LocationType(str, Enum):
    ROOM = "room"
    FACILITY = "facility"
    OFFICE = "office"
    MEETING = "meeting"
    DINING = "dining"
    STUDY = "study"
    ENTRANCE = "entrance"


class ConnectorType(str, Enum):
    ELEVATOR = "elevator"
    STAIRS = "stairs"
    ESCALATOR = "escalator"
    EMERGENCY_EXIT = "emergency_exit"


class Location(Document):
    location_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the location")
    name: Indexed(str) = Field(..., description="Name of the location")
    floor_id: str = Field(..., description="ID of the floor this location belongs to")
    category: LocationType = Field(..., description="Category of the location")
    shape: ShapeType = Field(..., description="Shape type - circle or rectangle")
    x: float = Field(..., description="X coordinate position")
    y: float = Field(..., description="Y coordinate position")
    width: Optional[float] = Field(None, description="Width for rectangle shape")
    height: Optional[float] = Field(None, description="Height for rectangle shape")
    radius: Optional[float] = Field(None, description="Radius for circle shape")
    logo_url: Optional[str] = Field(None, description="URL for location logo/icon")
    color: str = Field(default="#3b82f6", description="Color for location display")
    text_color: str = Field(default="#000000", description="Text color for location")
    is_published: bool = Field(default=True, description="Whether location is published")
    created_by: Optional[str] = Field(None, description="User who created the location")
    datetime: float = Field(default_factory=lambda: time.time(), description="Timestamp when location was created")
    updated_by: Optional[str] = Field(None, description="User who last updated the location")
    update_on: Optional[float] = Field(None, description="Timestamp of last update")
    status: str = Field(default="active", description="Status of the location")
    description: Optional[str] = Field(None, description="Description of the location")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    class Settings:
        name = "locations"


class VerticalConnector(Document):
    connector_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the connector")
    name: str = Field(..., description="Name of the connector (e.g., 'elv-a', 'stairs-1')")
    shared_id: str = Field(..., description="Shared identifier across floors (e.g., 'e', 'e1')")
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
    datetime: float = Field(default_factory=lambda: time.time(), description="Timestamp when connector was created")
    updated_by: Optional[str] = Field(None, description="User who last updated the connector")
    update_on: Optional[float] = Field(None, description="Timestamp of last update")
    status: str = Field(default="active", description="Status of the connector")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    class Settings:
        name = "vertical_connectors"


class PathPoint(BaseModel):
    x: float = Field(..., description="X coordinate of path point")
    y: float = Field(..., description="Y coordinate of path point")


# class Path(Document):
#     path_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the path")
#     name: str = Field(..., description="Name of the path")
#     floor_id: str = Field(..., description="ID of the floor this path belongs to")
#     source: str = Field(..., description="Source location name")
#     destination: str = Field(..., description="Destination location name")
#     source_tag_id: Optional[str] = Field(None, description="Source location/connector ID")
#     destination_tag_id: Optional[str] = Field(None, description="Destination location/connector ID")
#     points: List[PathPoint] = Field(..., description="Array of path points")
#     shape: ShapeType = Field(..., description="Shape type for path visualization")
#     width: Optional[float] = Field(None, description="Width for rectangle shape")
#     height: Optional[float] = Field(None, description="Height for rectangle shape")
#     radius: Optional[float] = Field(None, description="Radius for circle shape")
#     color: str = Field(..., description="Color for path display")
#     is_published: bool = Field(default=True, description="Whether path is published")
#     created_by: Optional[str] = Field(None, description="User who created the path")
#     datetime: float = Field(default_factory=lambda: time.time(), description="Timestamp when path was created")
#     updated_by: Optional[str] = Field(None, description="User who last updated the path")
#     update_on: Optional[float] = Field(None, description="Timestamp of last update")
#     status: str = Field(default="active", description="Status of the path")
#     metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

#     class Settings:
#         name = "paths"


# Add these new fields to the existing Path model
class Path(Document):
    path_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the path")
    name: str = Field(..., description="Name of the path")
    
    # Enhanced fields for multi-floor support
    building_id: Optional[str] = Field(None, description="Building ID (required for multi-floor paths)")
    floor_id: Optional[str] = Field(None, description="ID of the floor this path belongs to (for single-floor paths)")
    
    # Multi-floor specific fields
    is_multi_floor: bool = Field(default=False, description="Whether this is a multi-floor path")
    source_floor_id: Optional[str] = Field(None, description="Source floor ID (for multi-floor paths)")
    destination_floor_id: Optional[str] = Field(None, description="Destination floor ID (for multi-floor paths)")
    
    # Floor segments for multi-floor paths
    floor_segments: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Path segments for each floor (multi-floor only)")
    vertical_transitions: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Vertical connector transitions (multi-floor only)")
    total_floors: Optional[int] = Field(None, description="Total number of floors involved (multi-floor only)")
    
    # Existing fields remain the same
    source: str = Field(..., description="Source location name")
    destination: str = Field(..., description="Destination location name")
    source_tag_id: Optional[str] = Field(None, description="Source location/connector ID")
    destination_tag_id: Optional[str] = Field(None, description="Destination location/connector ID")
    points: List[PathPoint] = Field(..., description="Array of path points")
    shape: ShapeType = Field(..., description="Shape type for path visualization")
    width: Optional[float] = Field(None, description="Width for rectangle shape")
    height: Optional[float] = Field(None, description="Height for rectangle shape")
    radius: Optional[float] = Field(None, description="Radius for circle shape")
    color: str = Field(..., description="Color for path display")
    is_published: bool = Field(default=True, description="Whether path is published")
    created_by: Optional[str] = Field(None, description="User who created the path")
    datetime: float = Field(default_factory=lambda: time.time(), description="Timestamp when path was created")
    updated_by: Optional[str] = Field(None, description="User who last updated the path")
    update_on: Optional[float] = Field(None, description="Timestamp of last update")
    status: str = Field(default="active", description="Status of the path")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    class Settings:
        name = "paths"


class Floor(Document):
    floor_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the floor")
    name: Indexed(str) = Field(..., description="Name of the floor")
    building_id: Optional[str] = Field(None, description="Building identifier this floor belongs to")
    floor_number: int = Field(..., description="Floor number")
    # display_number: int = Field(..., description="Display number for UI")
    floor_plan_url: Optional[str] = Field(None, description="URL to floor plan image")
    locations: Optional[List[str]] = Field(default_factory=list, description="List of location IDs on this floor")
    vertical_connectors: Optional[List[str]] = Field(default_factory=list, description="List of vertical connector IDs on this floor")
    paths: Optional[List[str]] = Field(default_factory=list, description="List of path IDs on this floor")
    is_published: bool = Field(default=True, description="Whether floor is published")
    # created_by: Optional[str] = Field(None, description="User who created the floor")
    datetime: float = Field(default_factory=lambda: time.time(), description="Timestamp when floor was created")
    updated_by: Optional[str] = Field(None, description="User who last updated the floor")
    update_on: Optional[float] = Field(None, description="Timestamp of last update")
    status: str = Field(default="active", description="Status of the floor")
    description: Optional[str] = Field(None, description="Description of the floor")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    entity_uuid: Optional[str] = Field(None, description="Entity UUID for external systems")


    class Settings:
        name = "floors"


class Building(Document):
    building_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the building")
    name: Indexed(str) = Field(..., description="Name of the building")
    address: Optional[str] = Field(None, description="Building address")
    floors: Optional[List[str]] = Field(default_factory=list, description="List of floor IDs in this building")
    # created_by: Optional[str] = Field(None, description="User who created the building")
    datetime: float = Field(default_factory=lambda: time.time(), description="Timestamp when building was created")
    updated_by: Optional[str] = Field(None, description="User who last updated the building")
    update_on: Optional[float] = Field(None, description="Timestamp of last update")
    status: str = Field(default="active", description="Status of the building")
    description: Optional[str] = Field(None, description="Description of the building")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    entity_uuid: Optional[str] = Field(None, description="Entity UUID for external systems")

    class Settings:
        name = "buildings"


class Event(Document):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the event")
    title: str = Field(..., description="Event title")
    event_type: str = Field(..., description="Type of event")
    date: str = Field(..., description="Event date")
    image_url: Optional[str] = Field(None, description="Event image URL")
    description: Optional[str] = Field(None, description="Event description")
    location_id: Optional[str] = Field(None, description="Associated location ID")
    is_published: bool = Field(default=True, description="Whether event is published")
    created_by: Optional[str] = Field(None, description="User who created the event")
    datetime: float = Field(default_factory=lambda: time.time(), description="Timestamp when event was created")
    updated_by: Optional[str] = Field(None, description="User who last updated the event")
    update_on: Optional[float] = Field(None, description="Timestamp of last update")
    status: str = Field(default="active", description="Status of the event")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    class Settings:
        name = "events"


# Response Models for API
class MultiFloorRoute(BaseModel):
    total_floors: int = Field(..., description="Total number of floors in the route")
    route_segments: List[Dict[str, Any]] = Field(..., description="Route segments for each floor")
    vertical_transitions: List[Dict[str, Any]] = Field(..., description="Vertical connector transitions")
    estimated_time: Optional[int] = Field(None, description="Estimated time in minutes")


class NavigationRequest(BaseModel):
    source_location_id: str = Field(..., description="Source location ID")
    destination_location_id: str = Field(..., description="Destination location ID")
    building_id: str = Field(..., description="Building ID")
    preferred_connector_type: Optional[ConnectorType] = Field(None, description="Preferred vertical connector type")
