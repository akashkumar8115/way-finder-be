from fastapi import HTTPException, status, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import time
from sqlalchemy.ext.asyncio import AsyncSession

from src.datamodel.database.domain.DigitalSignage import EmergencyService
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db

logger = logging.getLogger(__name__)

# ---------- API CONFIG ----------
def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Emergency Service"],
        "summary": "Get Emergency Services",
        "response_model": dict,
        "description": "Retrieve all emergency services for an entity.",
        "response_description": "List of emergency services",
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

        emregency_service: List[EmergencyService] = await EmergencyService.find(
            {"entity_uuid": entity_uuid}
        ).to_list()

        if not emregency_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No emergency services found for entity_uuid: {entity_uuid}"
            )  
        
        # Convert to JSON-serializable format
        emregency_service_list = []
        for event in emregency_service:
            emregency_service_list.append({
                "emergency_service_uuid": str(event.emergency_service_uuid),
                "title": event.title,
                "description": event.description,
                "phone_number": event.phone_number,
                "location": event.location,
                "availability": event.availability,
                "priority_level": event.priority_level
            })
        return {"data": emregency_service_list, "count": len(emregency_service_list)}
        


    except Exception as e:
        logger.exception(f"Error retrieving emergency services: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve emergency services: {str(e)}"
        )
