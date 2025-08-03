from typing import List, Dict, Any, Optional, Tuple
from src.datamodel.database.domain.DigitalSignage import (
    Location, Floor, VerticalConnector, Path, NavigationRequest, MultiFloorRoute, PathPoint
)
import heapq
import math
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class NavigationService:
    def __init__(self):
        self.graph = defaultdict(list)
        self.vertical_connectors_map = defaultdict(list)
    
    async def find_multi_floor_route(self, request: NavigationRequest) -> MultiFloorRoute:
        """
        Find route between locations that may span multiple floors
        """
        try:
            # Get source and destination locations
            source_location = await Location.find_one(Location.location_id == request.source_location_id)
            destination_location = await Location.find_one(Location.location_id == request.destination_location_id)
            
            if not source_location or not destination_location:
                raise ValueError("Source or destination location not found")
            
            # Check if same floor
            if source_location.floor_id == destination_location.floor_id:
                return await self._find_single_floor_route(source_location, destination_location)
            
            # Multi-floor routing
            return await self._find_multi_floor_route(source_location, destination_location, request.preferred_connector_type)
        
        except Exception as e:
            logger.error(f"Error finding multi-floor route: {str(e)}")
            raise
    
    async def _find_multi_floor_route(
        self, 
        source: Location, 
        destination: Location, 
        preferred_connector: Optional[str] = None
    ) -> MultiFloorRoute:
        """
        Find route spanning multiple floors using vertical connectors
        """
        route_segments = []
        vertical_transitions = []
        
        try:
            # Step 1: Find path from source to vertical connector on source floor
            source_connectors = await self._get_floor_connectors(source.floor_id)
            best_source_connector = await self._find_nearest_connector(source, source_connectors, preferred_connector)
            
            if not best_source_connector:
                raise ValueError("No suitable vertical connector found on source floor")
            
            # Step 2: Find corresponding connector on destination floor
            dest_connectors = await self._get_connectors_by_shared_id(
                best_source_connector.shared_id, 
                destination.floor_id
            )
            
            if not dest_connectors:
                raise ValueError("No corresponding vertical connector found on destination floor")
            
            dest_connector = dest_connectors[0]
            
            # Step 3: Build route segments
            # Segment 1: Source to source connector
            source_to_connector = await self._find_path_on_floor(
                source.floor_id, 
                source.location_id, 
                best_source_connector.connector_id
            )
            
            if source_to_connector:
                route_segments.append({
                    "floor_id": source.floor_id,
                    "segment_type": "horizontal",
                    "path": source_to_connector,
                    "instructions": f"Walk from {source.name} to {best_source_connector.name}",
                    "distance": self._calculate_path_distance(source_to_connector.get("points", []))
                })
            
            # Vertical transition
            vertical_transitions.append({
                "connector_type": best_source_connector.connector_type,
                "connector_name": best_source_connector.name,
                "from_floor": source.floor_id,
                "to_floor": destination.floor_id,
                "shared_id": best_source_connector.shared_id,
                "instructions": f"Take {best_source_connector.connector_type} from floor {source.floor_id} to floor {destination.floor_id}",
                "estimated_time": self._get_connector_time(best_source_connector.connector_type)
            })
            
            # Segment 2: Destination connector to destination
            connector_to_dest = await self._find_path_on_floor(
                destination.floor_id,
                dest_connector.connector_id,
                destination.location_id
            )
            
            if connector_to_dest:
                route_segments.append({
                    "floor_id": destination.floor_id,
                    "segment_type": "horizontal", 
                    "path": connector_to_dest,
                    "instructions": f"Walk from {dest_connector.name} to {destination.name}",
                    "distance": self._calculate_path_distance(connector_to_dest.get("points", []))
                })
            
            # Calculate total estimated time
            total_time = sum([segment.get("distance", 0) * 0.5 for segment in route_segments])  # 0.5 min per unit
            total_time += sum([vt.get("estimated_time", 0) for vt in vertical_transitions])
            
            return MultiFloorRoute(
                total_floors=len(set([source.floor_id, destination.floor_id])),
                route_segments=route_segments,
                vertical_transitions=vertical_transitions,
                estimated_time=int(total_time)
            )
            
        except Exception as e:
            logger.error(f"Error in multi-floor routing: {str(e)}")
            raise
    
    async def _find_single_floor_route(self, source: Location, destination: Location) -> MultiFloorRoute:
        """
        Find route on single floor
        """
        try:
            path = await self._find_path_on_floor(
                source.floor_id,
                source.location_id,
                destination.location_id
            )
            
            route_segments = []
            if path:
                route_segments.append({
                    "floor_id": source.floor_id,
                    "segment_type": "horizontal",
                    "path": path,
                    "instructions": f"Walk from {source.name} to {destination.name}",
                    "distance": self._calculate_path_distance(path.get("points", []))
                })
            
            total_time = sum([segment.get("distance", 0) * 0.5 for segment in route_segments])
            
            return MultiFloorRoute(
                total_floors=1,
                route_segments=route_segments,
                vertical_transitions=[],
                estimated_time=int(total_time)
            )
            
        except Exception as e:
            logger.error(f"Error in single floor routing: {str(e)}")
            raise


    async def _get_floor_connectors(self, floor_id: str) -> List[VerticalConnector]:
        """
        Get all vertical connectors on a specific floor
        """
        try:
            connectors = await VerticalConnector.find(
                VerticalConnector.floor_id == floor_id,
                VerticalConnector.status == "active"
            ).to_list()
            return connectors
        except Exception as e:
            logger.error(f"Error getting floor connectors: {str(e)}")
            return []
    
    async def _get_connectors_by_shared_id(self, shared_id: str, floor_id: str) -> List[VerticalConnector]:
        """
        Get connectors with same shared_id on specific floor
        """
        try:
            connectors = await VerticalConnector.find(
                VerticalConnector.shared_id == shared_id,
                VerticalConnector.floor_id == floor_id,
                VerticalConnector.status == "active"
            ).to_list()
            return connectors
        except Exception as e:
            logger.error(f"Error getting connectors by shared ID: {str(e)}")
            return []
    
    async def _find_nearest_connector(
        self, 
        location: Location, 
        connectors: List[VerticalConnector],
        preferred_type: Optional[str] = None
    ) -> Optional[VerticalConnector]:
        """
        Find nearest vertical connector to a location
        """
        if not connectors:
            return None
        
        # Filter by preferred type if specified
        if preferred_type:
            filtered_connectors = [c for c in connectors if c.connector_type == preferred_type]
            if filtered_connectors:
                connectors = filtered_connectors
        
        # Calculate distances and find nearest
        nearest_connector = None
        min_distance = float('inf')
        
        for connector in connectors:
            distance = self._calculate_euclidean_distance(
                location.x, location.y,
                connector.x, connector.y
            )
            
            if distance < min_distance:
                min_distance = distance
                nearest_connector = connector
        
        return nearest_connector
    
    async def _find_path_on_floor(self, floor_id: str, source_id: str, destination_id: str) -> Optional[Dict[str, Any]]:
        """
        Find path between two points on the same floor
        """
        try:
            # Look for existing path
            path = await Path.find_one({
                "floor_id": floor_id,
                "$or": [
                    {"source_tag_id": source_id, "destination_tag_id": destination_id},
                    {"source_tag_id": destination_id, "destination_tag_id": source_id}
                ],
                "status": "active",
                "is_published": True
            })
            
            if path:
                return {
                    "path_id": path.path_id,
                    "name": path.name,
                    "points": [{"x": p.x, "y": p.y} for p in path.points],
                    "color": path.color,
                    "shape": path.shape,
                    "width": path.width,
                    "height": path.height,
                    "radius": path.radius
                }
            
            # If no direct path found, try to find indirect path through graph traversal
            return await self._find_indirect_path(floor_id, source_id, destination_id)
            
        except Exception as e:
            logger.error(f"Error finding path on floor: {str(e)}")
            return None
    
    async def _find_indirect_path(self, floor_id: str, source_id: str, destination_id: str) -> Optional[Dict[str, Any]]:
        """
        Find indirect path using graph traversal (Dijkstra's algorithm)
        """
        try:
            # Build graph for the floor
            graph = await self._build_floor_graph(floor_id)
            
            if source_id not in graph or destination_id not in graph:
                return None
            
            # Use Dijkstra's algorithm
            distances = {node: float('inf') for node in graph}
            distances[source_id] = 0
            previous = {}
            pq = [(0, source_id)]
            visited = set()
            
            while pq:
                current_distance, current_node = heapq.heappop(pq)
                
                if current_node in visited:
                    continue
                
                visited.add(current_node)
                
                if current_node == destination_id:
                    break
                
                for neighbor, weight in graph[current_node]:
                    distance = current_distance + weight
                    
                    if distance < distances[neighbor]:
                        distances[neighbor] = distance
                        previous[neighbor] = current_node
                        heapq.heappush(pq, (distance, neighbor))
            
            # Reconstruct path
            if destination_id not in previous and destination_id != source_id:
                return None
            
            path_nodes = []
            current = destination_id
            while current is not None:
                path_nodes.append(current)
                current = previous.get(current)
            
            path_nodes.reverse()
            
            # Convert to coordinate points
            points = await self._convert_nodes_to_points(path_nodes)
            
            return {
                "path_id": f"generated_{source_id}_{destination_id}",
                "name": f"Route to destination",
                "points": points,
                "color": "#3b82f6",
                "shape": "circle",
                "radius": 0.01
            }
            
        except Exception as e:
            logger.error(f"Error finding indirect path: {str(e)}")
            return None


    async def _build_floor_graph(self, floor_id: str) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build graph representation of floor with locations and connectors
        """
        graph = defaultdict(list)
        
        try:
            # Get all paths on the floor
            paths = await Path.find(
                Path.floor_id == floor_id,
                Path.status == "active",
                Path.is_published == True
            ).to_list()
            
            for path in paths:
                if path.source_tag_id and path.destination_tag_id:
                    # Calculate weight based on path distance
                    weight = self._calculate_path_distance([{"x": p.x, "y": p.y} for p in path.points])
                    
                    # Add bidirectional edges
                    graph[path.source_tag_id].append((path.destination_tag_id, weight))
                    graph[path.destination_tag_id].append((path.source_tag_id, weight))
            
            return dict(graph)
            
        except Exception as e:
            logger.error(f"Error building floor graph: {str(e)}")
            return {}
    
    async def _convert_nodes_to_points(self, node_ids: List[str]) -> List[Dict[str, float]]:
        """
        Convert node IDs to coordinate points
        """
        points = []
        
        try:
            for node_id in node_ids:
                # Try to find as location first
                location = await Location.find_one(Location.location_id == node_id)
                if location:
                    points.append({"x": location.x, "y": location.y})
                    continue
                
                # Try to find as vertical connector
                connector = await VerticalConnector.find_one(VerticalConnector.connector_id == node_id)
                if connector:
                    points.append({"x": connector.x, "y": connector.y})
            
            return points
            
        except Exception as e:
            logger.error(f"Error converting nodes to points: {str(e)}")
            return []
    
    def _calculate_euclidean_distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """
        Calculate Euclidean distance between two points
        """
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    def _calculate_path_distance(self, points: List[Dict[str, float]]) -> float:
        """
        Calculate total distance of a path
        """
        if len(points) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(1, len(points)):
            distance = self._calculate_euclidean_distance(
                points[i-1]["x"], points[i-1]["y"],
                points[i]["x"], points[i]["y"]
            )
            total_distance += distance
        
        return total_distance
    
    def _get_connector_time(self, connector_type: str) -> int:
        """
        Get estimated time for using different connector types (in minutes)
        """
        time_map = {
            "elevator": 3,
            "stairs": 2,
            "escalator": 1,
            "ramp": 2
        }
        return time_map.get(connector_type.lower(), 2)
    
    async def get_floor_locations(self, floor_id: str) -> List[Dict[str, Any]]:
        """
        Get all locations on a specific floor
        """
        try:
            locations = await Location.find(
                Location.floor_id == floor_id,
                Location.status == "active"
            ).to_list()
            
            return [
                {
                    "location_id": loc.location_id,
                    "name": loc.name,
                    "category": loc.category,
                    "x": loc.x,
                    "y": loc.y,
                    "shape": loc.shape,
                    "width": loc.width,
                    "height": loc.height,
                    "radius": loc.radius,
                    "logo_url": loc.logo_url,
                    "description": loc.description
                }
                for loc in locations
            ]
            
        except Exception as e:
            logger.error(f"Error getting floor locations: {str(e)}")
            return []
    
    async def get_floor_connectors(self, floor_id: str) -> List[Dict[str, Any]]:
        """
        Get all vertical connectors on a specific floor
        """
        try:
            connectors = await VerticalConnector.find(
                VerticalConnector.floor_id == floor_id,
                VerticalConnector.status == "active"
            ).to_list()
            
            return [
                {
                    "connector_id": conn.connector_id,
                    "name": conn.name,
                    "connector_type": conn.connector_type,
                    "x": conn.x,
                    "y": conn.y,
                    "shared_id": conn.shared_id,
                    "description": conn.description
                }
                for conn in connectors
            ]
            
        except Exception as e:
            logger.error(f"Error getting floor connectors: {str(e)}")
            return []
    
    async def get_floor_paths(self, floor_id: str) -> List[Dict[str, Any]]:
        """
        Get all paths on a specific floor
        """
        try:
            paths = await Path.find(
                Path.floor_id == floor_id,
                Path.status == "active",
                Path.is_published == True
            ).to_list()
            
            return [
                {
                    "path_id": path.path_id,
                    "name": path.name,
                    "source_tag_id": path.source_tag_id,
                    "destination_tag_id": path.destination_tag_id,
                    "points": [{"x": p.x, "y": p.y} for p in path.points],
                    "color": path.color,
                    "shape": path.shape,
                    "width": path.width,
                    "height": path.height,
                    "radius": path.radius,
                    "description": path.description
                }
                for path in paths
            ]
            
        except Exception as e:
            logger.error(f"Error getting floor paths: {str(e)}")
            return []
    
    async def validate_navigation_request(self, request: NavigationRequest) -> Dict[str, Any]:
        """
        Validate navigation request and return validation results
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Check if source location exists
            source_location = await Location.find_one(
                Location.location_id == request.source_location_id,
                Location.status == "active"
            )
            
            if not source_location:
                validation_result["is_valid"] = False
                validation_result["errors"].append("Source location not found or inactive")
            
            # Check if destination location exists
            destination_location = await Location.find_one(
                Location.location_id == request.destination_location_id,
                Location.status == "active"
            )
            
            if not destination_location:
                validation_result["is_valid"] = False
                validation_result["errors"].append("Destination location not found or inactive")
            
            # Check if preferred connector type is valid
            if request.preferred_connector_type:
                valid_types = ["elevator", "stairs", "escalator", "ramp"]
                if request.preferred_connector_type.lower() not in valid_types:
                    validation_result["warnings"].append(
                        f"Invalid connector type '{request.preferred_connector_type}'. Valid types: {valid_types}"
                    )
            
            # Check if locations are on different floors and connectors exist
            if source_location and destination_location:
                if source_location.floor_id != destination_location.floor_id:
                    source_connectors = await self._get_floor_connectors(source_location.floor_id)
                    dest_connectors = await self._get_floor_connectors(destination_location.floor_id)
                    
                    if not source_connectors:
                        validation_result["is_valid"] = False
                        validation_result["errors"].append("No vertical connectors found on source floor")
                    
                    if not dest_connectors:
                        validation_result["is_valid"] = False
                        validation_result["errors"].append("No vertical connectors found on destination floor")
                    
                    # Check if there are matching connectors between floors
                    if source_connectors and dest_connectors:
                        source_shared_ids = {c.shared_id for c in source_connectors}
                        dest_shared_ids = {c.shared_id for c in dest_connectors}
                        
                        if not source_shared_ids.intersection(dest_shared_ids):
                            validation_result["is_valid"] = False
                            validation_result["errors"].append("No connecting vertical connectors found between floors")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating navigation request: {str(e)}")
            return {
                "is_valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }


# Create global instance
navigation_service = NavigationService()
