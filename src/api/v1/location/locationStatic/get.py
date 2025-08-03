from fastapi import HTTPException, Query, status
from pydantic import BaseModel
from typing import Optional, Dict, List
import logging
from src.datamodel.database.domain.DigitalSignage import Location
from src.datamodel.datavalidation.apiconfig import ApiConfig


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Location"],
        "summary": "Get Location Statistics",
        "response_model": dict,
        "description": "Get comprehensive statistics about locations including counts by category, shape, status, floor, etc.",
        "response_description": "Location statistics",
        "deprecated": False,
    }
    return ApiConfig(**config)


class CategoryStats(BaseModel):
    category: str
    count: int
    percentage: float


class ShapeStats(BaseModel):
    shape: str
    count: int
    percentage: float


class StatusStats(BaseModel):
    status: str
    count: int
    percentage: float


class FloorStats(BaseModel):
    floor_id: str
    count: int
    percentage: float
    active_locations: int
    inactive_locations: int
    deleted_locations: int


class LocationStatisticsResponse(BaseModel):
    total_locations: int
    active_locations: int
    inactive_locations: int
    deleted_locations: int
    total_floors: int
    categories: List[CategoryStats]
    shapes: List[ShapeStats]
    status_breakdown: List[StatusStats]
    floor_breakdown: List[FloorStats]
    locations_with_logos: int
    locations_with_descriptions: int
    average_coordinates: Dict[str, float]
    average_coordinates_per_floor: Dict[str, Dict[str, float]]

    class Config:
        allow_population_by_field_name = True


async def main(
    include_deleted: Optional[bool] = Query(False, description="Include deleted locations in statistics"),
    floor_id: Optional[str] = Query(None, description="Get statistics for a specific floor only")
):
    try:
        # Build query filter
        query_filter = {}
        if not include_deleted:
            query_filter["status"] = {"$ne": "deleted"}
        
        if floor_id:
            query_filter["floor_id"] = floor_id

        # Get all locations
        locations = await Location.find(query_filter).to_list()
        
        if not locations:
            return {
                "status": "success",
                "message": "No locations found",
                "data": LocationStatisticsResponse(
                    total_locations=0,
                    active_locations=0,
                    inactive_locations=0,
                    deleted_locations=0,
                    total_floors=0,
                    categories=[],
                    shapes=[],
                    status_breakdown=[],
                    floor_breakdown=[],
                    locations_with_logos=0,
                    locations_with_descriptions=0,
                    average_coordinates={"x": 0.0, "y": 0.0},
                    average_coordinates_per_floor={}
                )
            }

        total_locations = len(locations)
        
        # Count by status
        status_counts = {}
        for location in locations:
            status = location.status
            status_counts[status] = status_counts.get(status, 0) + 1

        # Count by category
        category_counts = {}
        for location in locations:
            category = location.category
            category_counts[category] = category_counts.get(category, 0) + 1

        # Count by shape
        shape_counts = {}
        for location in locations:
            shape = location.shape.value
            shape_counts[shape] = shape_counts.get(shape, 0) + 1

        # Count by floor and detailed floor statistics
        floor_counts = {}
        floor_details = {}
        for location in locations:
            floor = location.floor_id
            floor_counts[floor] = floor_counts.get(floor, 0) + 1
            
            if floor not in floor_details:
                floor_details[floor] = {
                    "active": 0,
                    "inactive": 0,
                    "deleted": 0,
                    "coordinates": {"x": [], "y": []}
                }
            
            floor_details[floor][location.status] += 1
            floor_details[floor]["coordinates"]["x"].append(location.x)
            floor_details[floor]["coordinates"]["y"].append(location.y)

        # Count locations with logos and descriptions
        locations_with_logos = sum(1 for loc in locations if loc.logo_url)
        locations_with_descriptions = sum(1 for loc in locations if loc.description)

        # Calculate overall average coordinates
        total_x = sum(loc.x for loc in locations)
        total_y = sum(loc.y for loc in locations)
        avg_x = total_x / total_locations if total_locations > 0 else 0.0
        avg_y = total_y / total_locations if total_locations > 0 else 0.0

        # Calculate average coordinates per floor
        average_coordinates_per_floor = {}
        for floor, details in floor_details.items():
            coords = details["coordinates"]
            if coords["x"] and coords["y"]:
                avg_floor_x = sum(coords["x"]) / len(coords["x"])
                avg_floor_y = sum(coords["y"]) / len(coords["y"])
                average_coordinates_per_floor[floor] = {
                    "x": round(avg_floor_x, 2),
                    "y": round(avg_floor_y, 2)
                }

        # Prepare category statistics
        category_stats = []
        for category, count in category_counts.items():
            percentage = (count / total_locations) * 100
            category_stats.append(CategoryStats(
                category=category,
                count=count,
                percentage=round(percentage, 2)
            ))
        category_stats.sort(key=lambda x: x.count, reverse=True)

        # Prepare shape statistics
        shape_stats = []
        for shape, count in shape_counts.items():
            percentage = (count / total_locations) * 100
            shape_stats.append(ShapeStats(
                shape=shape,
                count=count,
                percentage=round(percentage, 2)
            ))
        shape_stats.sort(key=lambda x: x.count, reverse=True)

        # Prepare status statistics
        status_breakdown = []
        for status, count in status_counts.items():
            percentage = (count / total_locations) * 100
            status_breakdown.append(StatusStats(
                status=status,
                count=count,
                percentage=round(percentage, 2)
            ))
        status_breakdown.sort(key=lambda x: x.count, reverse=True)

        # Prepare floor statistics
        floor_breakdown = []
        for floor, count in floor_counts.items():
            percentage = (count / total_locations) * 100
            details = floor_details[floor]
            floor_breakdown.append(FloorStats(
                floor_id=floor,
                count=count,
                percentage=round(percentage, 2),
                active_locations=details["active"],
                inactive_locations=details["inactive"],
                deleted_locations=details["deleted"]
            ))
        floor_breakdown.sort(key=lambda x: x.count, reverse=True)

        # Create response
        response = LocationStatisticsResponse(
            total_locations=total_locations,
            active_locations=status_counts.get("active", 0),
            inactive_locations=status_counts.get("inactive", 0),
            deleted_locations=status_counts.get("deleted", 0),
            total_floors=len(floor_counts),
            categories=category_stats,
            shapes=shape_stats,
            status_breakdown=status_breakdown,
            floor_breakdown=floor_breakdown,
            locations_with_logos=locations_with_logos,
            locations_with_descriptions=locations_with_descriptions,
            average_coordinates={
                "x": round(avg_x, 2),
                "y": round(avg_y, 2)
            },
            average_coordinates_per_floor=average_coordinates_per_floor
        )

        filter_message = f" for floor {floor_id}" if floor_id else ""
        logger.info(f"Generated statistics for {total_locations} locations{filter_message}")

        return {
            "status": "success",
            "message": f"Statistics generated for {total_locations} locations{filter_message}",
            "data": response
        }

    except Exception as e:
        logger.exception(f"Error generating location statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate location statistics: {str(e)}"
        )
