from fastapi import HTTPException, status, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import time
from sqlalchemy.ext.asyncio import AsyncSession
from src.datamodel.database.domain.DigitalSignage import Department
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db

logger = logging.getLogger(__name__)

# ---------- API CONFIG ----------
def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Department Service"],
        "summary": "Get Department Services",
        "response_model": dict,
        "description": "Retrieve all Department services for an entity.",
        "response_description": "List of Department  services",
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

        emregency_service: List[Department] = await Department.find({}).to_list()

        # Convert to JSON-serializable format
        emregency_alert_list = []
        for event in emregency_service:
            emregency_alert_list.append({
                "id": event.id,
                "name": event.name,
                "description": event.description,
                "phone_number": event.phone_number,
                "location":event.location,
                "hours": event.hours,
                "services":event.services
            })

        return {"data": emregency_alert_list, "count": len(emregency_alert_list)}
        


    except Exception as e:
        logger.exception(f"Error retrieving Docter services: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve Docter services: {str(e)}"
        )
