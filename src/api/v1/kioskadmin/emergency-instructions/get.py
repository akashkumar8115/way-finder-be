from fastapi import HTTPException, status, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import time
from sqlalchemy.ext.asyncio import AsyncSession
from src.datamodel.database.domain.DigitalSignage import EmergencyInstruction
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db

logger = logging.getLogger(__name__)

# ---------- API CONFIG ----------
def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["EmergencyInstruction Service"],
        "summary": "Get NonEmergEmergencyInstructionencyContact Services",
        "response_model": dict,
        "description": "Retrieve all EmergencyInstruction services for an entity.",
        "response_description": "List of EmergencyInstruction  services",
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

        emregency_service: List[EmergencyInstruction] = (
            await EmergencyInstruction.find({"entity_uuid": entity_uuid}).to_list()
        )

        if not emregency_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No emergency instruction found for entity_uuid: {entity_uuid}"
            )  
        # Convert to JSON-serializable format
        emregency_alert_list = []
        for event in emregency_service:
            emregency_alert_list.append({
                "id": event.id,
                "instruction_type": event.instruction_type,
                "title": event.title,
                "priority_level": event.priority_level,
                "content": event.content,
                "is_active": event.is_active
            })

        return {"data": emregency_alert_list, "count": len(emregency_alert_list)}
        


    except Exception as e:
        logger.exception(f"Error retrieving NonEmergencyContact services: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve NonEmergencyContact services: {str(e)}"
        )
