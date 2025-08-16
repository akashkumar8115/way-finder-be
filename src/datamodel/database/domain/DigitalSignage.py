from beanie import Document, Indexed
from pydantic import Field, BaseModel
from typing import Optional, Dict, List, Any
from enum import Enum
import time
import uuid

# -----------------------------
# Enums
# -----------------------------

class ShapeType(str, Enum):
    CIRCLE = "circle"
    RECTANGLE = "rectangle"


class LocationType(str, Enum):
    # Entrances & Exits
    ENTRANCE = "entrance"
    EXIT = "exit"
    EMERGENCY_EXIT = "emergency_exit"

    # Stores & Retail
    STORE = "store"
    SUPERMARKET = "supermarket"
    CLOTHING_STORE = "clothing_store"
    ELECTRONICS_STORE = "electronics_store"
    BOOKSTORE = "bookstore"
    TOY_STORE = "toy_store"
    JEWELRY_STORE = "jewelry_store"
    BEAUTY_STORE = "beauty_store"
    HOME_DECOR_STORE = "home_decor_store"
    FOOTWEAR_STORE = "footwear_store"

    # Dining
    DINING = "dining"
    FOOD_COURT = "food_court"
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    FAST_FOOD = "fast_food"
    ICE_CREAM_SHOP = "ice_cream_shop"

    # Entertainment
    CINEMA = "cinema"
    ARCADE = "arcade"
    PLAY_AREA = "play_area"
    BOWLING_ALLEY = "bowling_alley"
    EVENT_HALL = "event_hall"

    # Services
    RECEPTION = "reception"
    CUSTOMER_SERVICE = "customer_service"
    INFORMATION_DESK = "information_desk"
    SECURITY_OFFICE = "security_office"
    FIRST_AID = "first_aid"
    ATM = "atm"
    BANK = "bank"
    MONEY_EXCHANGE = "money_exchange"
    LOST_AND_FOUND = "lost_and_found"

    # Facilities
    RESTROOM = "restroom"
    MALE_RESTROOM = "male_restroom"
    FEMALE_RESTROOM = "female_restroom"
    FAMILY_RESTROOM = "family_restroom"
    WHEELCHAIR_ACCESS = "wheelchair_access"
    ELEVATOR = "elevator"
    ESCALATOR = "escalator"
    STAIRCASE = "staircase"

    # Back Office / Staff Areas
    OFFICE = "office"
    STAFF_ROOM = "staff_room"
    STORAGE = "storage"
    LOADING_DOCK = "loading_dock"
    MAINTENANCE_ROOM = "maintenance_room"

    # Parking & Transportation
    PARKING = "parking"
    BIKE_PARKING = "bike_parking"
    TAXI_STAND = "taxi_stand"
    BUS_STOP = "bus_stop"

    # Miscellaneous
    KIOSK = "kiosk"
    VENDING_MACHINE = "vending_machine"
    PHOTO_BOOTH = "photo_booth"
    CHARGING_STATION = "charging_station"
    SMOKING_AREA = "smoking_area"


class ConnectorType(str, Enum):
    ELEVATOR = "elevator"
    STAIRS = "stairs"
    ESCALATOR = "escalator"
    EMERGENCY_EXIT = "emergency_exit"


# -----------------------------
# Existing Documents (unchanged)
# -----------------------------

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


class Floor(Document):
    floor_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the floor")
    name: Indexed(str) = Field(..., description="Name of the floor")
    building_id: Optional[str] = Field(None, description="Building identifier this floor belongs to")
    floor_number: int = Field(..., description="Floor number")
    floor_plan_url: Optional[str] = Field(None, description="URL to floor plan image")
    locations: Optional[List[str]] = Field(default_factory=list, description="List of location IDs on this floor")
    vertical_connectors: Optional[List[str]] = Field(default_factory=list, description="List of vertical connector IDs on this floor")
    paths: Optional[List[str]] = Field(default_factory=list, description="List of path IDs on this floor")
    is_published: bool = Field(default=True, description="Whether floor is published")
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
    event_id: str = Field(description="Unique identifier for the event")
    name: str = Field(..., description="Event title")
    start_date: str = Field(..., description="Event start date")
    end_date: str = Field(..., description="Event end date")
    image_url: Optional[str] = Field(None, description="Event image URL")
    description: Optional[str] = Field(None, description="Event description")
    is_published: bool = Field(default=True, description="Whether event is published")
    created_by: Optional[str] = Field(None, description="User who created the event")
    updated_by: Optional[str] = Field(None, description="User who last updated the event")
    updated_on: Optional[float] = Field(None, description="Timestamp of last update")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    class Settings:
        name = "events"


# -----------------------------
# Path Models (new)
# -----------------------------

class NodeKind(str, Enum):
    LOCATION = "location"              # References Location.location_id
    VERTICAL_CONNECTOR = "vertical_connector"  # References VerticalConnector.connector_id
    WAYPOINT = "waypoint"              # Ad-hoc point with coordinates only


class PathPoint(BaseModel):
    kind: NodeKind = Field(..., description="Type of point in the path")
    ref_id: Optional[str] = Field(
        None,
        description="ID of referenced entity (Location.location_id or VerticalConnector.connector_id) when applicable"
    )
    shared_id: Optional[str] = Field(
        None,
        description="VerticalConnector.shared_id for cross-floor continuity (useful for queries/analytics)"
    )
    x: Optional[float] = Field(None, description="X coordinate (use for WAYPOINT or denormalized geometry)")
    y: Optional[float] = Field(None, description="Y coordinate (use for WAYPOINT or denormalized geometry)")


class FloorSegment(BaseModel):
    floor_id: str = Field(..., description="Floor this segment belongs to")
    sequence: int = Field(..., ge=0, description="Order of the segment within the path")
    points: List[PathPoint] = Field(..., min_items=2, description="Ordered points traversed on this floor")


class Path(Document):
    path_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the path")
    name: Optional[str] = Field(None, description="Human-friendly name for the path")
    building_id: Indexed(str) = Field(..., description="Building this path belongs to")
    created_by: Optional[Indexed(str)] = Field(None, description="User who created the path")

    # Endpoints (can be a Location, VerticalConnector, or Waypoint)
    start_point_id : str = Field(default=False, description="Starting point Id")
    end_point_id : str = Field(default=False, description="End point Id")

    # Publication & behavior
    is_published: bool = Field(default=False, description="Whether the path is published")
    # Geometry
    floor_segments: List[FloorSegment] = Field(..., description="Per-floor segments forming the path")

    # Denormalized helpers for fast queries (auto-fill via recompute_denorm())
    floors: List[str] = Field(default_factory=list, description="Distinct floor IDs touched by this path")
    connector_shared_ids: List[str] = Field(default_factory=list, description="Distinct vertical connector shared_ids used")
    is_multifloor: bool = Field(default=False, description="Derived: True if floors length > 1")
    # Common metadata
    tags: List[str] = Field(default_factory=list, description="Search/filter tags")
    datetime: float = Field(default_factory=lambda: time.time(), description="Creation timestamp")
    updated_by: Optional[str] = Field(None, description="User who last updated the path")
    update_on: Optional[float] = Field(None, description="Timestamp of last update")
    status: str = Field(default="active", description="Status of the path")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    class Settings:
        name = "paths"
        indexes = [
            "building_id",                           # fast building filters
            "created_by",                            # fast creator filters
            [("building_id", 1), ("created_by", 1)], # compound
            "floors",                                # multikey index for floor filters
            "is_published"                           # publishing filters
        ]

    # Utility: call this before save/update to keep denormalized fields consistent.
    def recompute_denorm(self) -> None:
        # Floors seen across all segments
        fset = {seg.floor_id for seg in (self.floor_segments or [])}
        self.floors = sorted(fset)
        self.is_multifloor = len(self.floors) > 1

        # Collect shared_ids from vertical connectors used in points
        shared_ids = []
        for seg in self.floor_segments or []:
            for p in seg.points or []:
                if p.kind == NodeKind.VERTICAL_CONNECTOR and p.shared_id:
                    shared_ids.append(p.shared_id)
        self.connector_shared_ids = sorted(set(shared_ids))
