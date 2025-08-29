from fastapi import HTTPException, Depends, status, Form, Request
from pydantic import BaseModel, Field
from typing import Optional
import time
import logging
import uuid

from src.datamodel.database.domain.DigitalSignage import EmergencyService
from src.datamodel.datavalidation.apiconfig import ApiConfig
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db

logger = logging.getLogger(__name__)

# ---------- API CONFIG ----------
def api_config():
    config = {
        "path": "",
        "status_code": 201,
        "tags": ["Emergency Service"],
        "summary": "Create Emergency Service",
        "response_model": dict,
        "description": "Create a new emergency service entry with optional icon upload.",
        "response_description": "Created emergency service data",
        "deprecated": False,
    }
    return ApiConfig(**config)


# ---------- REQUEST MODEL ----------
class EmergencyServiceCreateRequest(BaseModel):
    title: str = Field(..., description="Service title (e.g., 'Emergency Room', 'Ambulance')")
    description: Optional[str] = Field(None, description="Service description")
    phone_number: str = Field(..., description="Primary contact number")
    location: Optional[str] = Field(None, description="Location or area for the service")
    availability: Optional[str] = Field(None, description="Availability (e.g., '24 hours')")
    priority_level: int = Field(1, ge=1, le=5, description="Priority level 1 (highest) to 5 (lowest)")

    class Config:
        allow_population_by_field_name = True


# ---------- CREATE HANDLER ----------
async def main(
    request: Request,
    title: str = Form(..., description="Service title"),
    phone_number: str = Form(..., description="Primary contact number"),
    description: Optional[str] = Form(None, description="Service description"),
    location: Optional[str] = Form(None, description="Location/area"),
    availability: Optional[str] = Form(None, description="Availability"),
    priority_level: int = Form(1, description="Priority (1-5)"),
    db: AsyncSession = Depends(db),
):
    # 1) Validate token & capture entity
    validate_token_start = time.time()
    validate_token(request)
    entity_uuid = request.state.entity_uuid
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    try:
        # 2) Validate input (no UUID here, we’ll generate it later)
        service_data = EmergencyServiceCreateRequest(
            title=title,
            description=description,
            phone_number=phone_number,
            location=location,
            availability=availability,
            priority_level=priority_level,
        )

        # 3) Duplicate checks
        existing_by_title = await EmergencyService.find_one({
            "title": service_data.title,
            "entity_uuid": entity_uuid,
            "status": "active"
        })
        if existing_by_title:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Emergency service with title '{service_data.title}' already exists"
            )

        existing_by_phone = await EmergencyService.find_one({
            "phone_number": service_data.phone_number,
            "entity_uuid": entity_uuid,
            "status": "active"
        })
        if existing_by_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Emergency service with phone '{service_data.phone_number}' already exists"
            )

        # 4) Generate UUID and insert
        service_id = str(uuid.uuid4())
        new_service = EmergencyService(
            emergency_service_uuid=service_id,
            title=service_data.title,
            description=service_data.description,
            phone_number=service_data.phone_number,
            location=service_data.location,
            availability=service_data.availability,
            priority_level=service_data.priority_level,
        )
        await new_service.insert()

        logger.info(f"Emergency service created successfully: {service_id}")

        # 5) Simple dict response (no response model)
        return {
            "status": "success",
            "message": "Emergency service created successfully",
            "data": {
                "emergency_service_uuid": service_id,
                "title": new_service.title,
                "description": new_service.description,
                "phone_number": new_service.phone_number,
                "location": new_service.location,
                "availability": new_service.availability,
                "priority_level": new_service.priority_level,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating emergency service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create emergency service: {str(e)}"
        )
