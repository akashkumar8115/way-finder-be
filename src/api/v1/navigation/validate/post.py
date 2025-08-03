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
        "path": "/validate",
        "status_code": 200,
        "tags": ["Navigation"],
        "summary": "Validate Navigation Request",
        "response_model": dict,
        "description": "Validate a navigation request before finding the route.",
        "response_description": "Validation results",
        "deprecated": False,
    }
    return ApiConfig(**config)

class NavigationValidationRequest(BaseModel):
    source_location_id: str = Field(..., description="Source location ID")
    destination_location_id: str = Field(..., description="Destination location ID")
    building_id: str = Field(..., description="Building ID")
    preferred_connector_type: Optional[ConnectorType] = Field(None, description="Preferred vertical connector type")

    class Config:
        allow_population_by_field_name = True

async def main(validation_request: NavigationValidationRequest):
    try:
        # Create NavigationRequest object
        nav_request = NavigationRequest(
            source_location_id=validation_request.source_location_id,
            destination_location_id=validation_request.destination_location_id,
            building_id=validation_request.building_id,
            preferred_connector_type=validation_request.preferred_connector_type
        )

        # Validate the navigation request
        validation_result = await navigation_service.validate_navigation_request(nav_request)
        
        logger.info(f"Navigation request validation completed for {validation_request.source_location_id} to {validation_request.destination_location_id}")

        return {
            "status": "success",
            "message": "Navigation request validation completed",
            "data": {
                "validation": validation_result,
                "request": {
                    "source_location_id": validation_request.source_location_id,
                    "destination_location_id": validation_request.destination_location_id,
                    "building_id": validation_request.building_id,
                    "preferred_connector_type": validation_request.preferred_connector_type
                }
            }
        }

    except Exception as e:
        logger.exception(f"Error validating navigation request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate navigation request: {str(e)}"
        )
