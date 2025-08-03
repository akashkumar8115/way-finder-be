from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
import logging
from src.datamodel.database.domain.DigitalSignage import NavigationRequest, ConnectorType
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.services.navigation_service import navigation_service

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Navigation"],
        "summary": "Find Navigation Route",
        "response_model": dict,
        "description": "Find the best navigation route between two locations, supporting multi-floor navigation.",
        "response_description": "Navigation route with step-by-step directions",
        "deprecated": False,
    }
    return ApiConfig(**config)

class NavigationRouteRequest(BaseModel):
    source_location_id: str = Field(..., description="Source location ID")
    destination_location_id: str = Field(..., description="Destination location ID")
    building_id: str = Field(..., description="Building ID")
    preferred_connector_type: Optional[ConnectorType] = Field(None, description="Preferred vertical connector type")

    class Config:
        allow_population_by_field_name = True

async def main(navigation_request: NavigationRouteRequest):
    try:
        # Create NavigationRequest object
        nav_request = NavigationRequest(
            source_location_id=navigation_request.source_location_id,
            destination_location_id=navigation_request.destination_location_id,
            building_id=navigation_request.building_id,
            preferred_connector_type=navigation_request.preferred_connector_type
        )

        # Validate the navigation request
        validation_result = await navigation_service.validate_navigation_request(nav_request)
        
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Invalid navigation request",
                    "errors": validation_result["errors"],
                    "warnings": validation_result.get("warnings", [])
                }
            )

        # Find the route
        route = await navigation_service.find_multi_floor_route(nav_request)
        
        logger.info(f"Navigation route found from {navigation_request.source_location_id} to {navigation_request.destination_location_id}")

        return {
            "status": "success",
            "message": "Navigation route found successfully",
            "data": {
                "route": {
                    "total_floors": route.total_floors,
                    "route_segments": route.route_segments,
                    "vertical_transitions": route.vertical_transitions,
                    "estimated_time": route.estimated_time
                },
                "request": {
                    "source_location_id": navigation_request.source_location_id,
                    "destination_location_id": navigation_request.destination_location_id,
                    "building_id": navigation_request.building_id,
                    "preferred_connector_type": navigation_request.preferred_connector_type
                },
                "validation": {
                    "warnings": validation_result.get("warnings", [])
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error finding navigation route: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find navigation route: {str(e)}"
        )
