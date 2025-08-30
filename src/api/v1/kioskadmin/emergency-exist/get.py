from fastapi import HTTPException, status, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import time
from sqlalchemy.ext.asyncio import AsyncSession
from src.datamodel.database.domain.DigitalSignage import EmergencyExit
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db

logger = logging.getLogger(__name__)

# ---------- API CONFIG ----------
def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["emregency_alert_list Service"],
        "summary": "Get emregency_alert_list Services",
        "response_model": dict,
        "description": "Retrieve all emregency_alert_list services for an entity.",
        "response_description": "List of emregency_alert_list services",
        "deprecated": False,
    }
    return ApiConfig(**config)


# ---------- GET HANDLER ----------
async def main(
    request: Request,
    db: AsyncSession = Depends(db)
):
    # Validate token
    validate_token_start = time.time()
    validate_token(request)
    entity_uuid = request.state.entity_uuid
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    try:

        emregency_service: List[EmergencyExit] = await EmergencyExit.find({}).to_list()

        # Convert to JSON-serializable format
        emregency_alert_list = []
        for event in emregency_service:
            emregency_alert_list.append({
         "id": event.id,
         "name": event.name,
         "description": event.description,
         "direction_instructions": event.direction_instructions,
         "distance_meters": event.distance_meters,
         "estimated_time_minutes": event.estimated_time_minutes,
         "is_primary_exit": event.is_primary_exit,
         'floor_location': event.floor_location,
          "is_active": event.is_active,
          "display_order": event.display_order,
            })

        return {"data": emregency_alert_list, "count": len(emregency_alert_list)}
        


    except Exception as e:
        logger.exception(f"Error retrieving emregency_alert_list services: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve emregency_alert_list services: {str(e)}"
        )
