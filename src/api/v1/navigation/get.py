from fastapi import HTTPException, Path as FastAPIPath, Query, status
from typing import Optional
import logging
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.services.navigation_service import navigation_service

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Navigation"],
        "summary": "Get Floor Navigation Data",
        "response_model": dict,
        "description": "Get all navigation-related data for a specific floor (locations, connectors, paths).",
        "response_description": "Floor navigation data",
        "deprecated": False,
    }
    return ApiConfig(**config)

async def main(
    floor_id: str = FastAPIPath(..., description="Floor ID to get navigation data for"),
    include_locations: bool = Query(True, description="Include locations in response"),
    include_connectors: bool = Query(True, description="Include vertical connectors in response"),
    include_paths: bool = Query(True, description="Include paths in response")
):
    try:
        response_data = {
            "floor_id": floor_id
        }

        # Get locations if requested
        if include_locations:
            locations = await navigation_service.get_floor_locations(floor_id)
            response_data["locations"] = locations

        # Get vertical connectors if requested
        if include_connectors:
            connectors = await navigation_service.get_floor_connectors(floor_id)
            response_data["vertical_connectors"] = connectors

        # Get paths if requested
        if include_paths:
            paths = await navigation_service.get_floor_paths(floor_id)
            response_data["paths"] = paths

        # Calculate summary statistics
        summary = {
            "total_locations": len(response_data.get("locations", [])),
            "total_connectors": len(response_data.get("vertical_connectors", [])),
            "total_paths": len(response_data.get("paths", []))
        }
        response_data["summary"] = summary

        logger.info(f"Floor navigation data retrieved for floor: {floor_id}")

        return {
            "status": "success",
            "message": "Floor navigation data retrieved successfully",
            "data": response_data
        }

    except Exception as e:
        logger.exception(f"Error retrieving floor navigation data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve floor navigation data: {str(e)}"
        )
