from fastapi import HTTPException, Depends, status, Request
import time
import logging
import uuid
from pydantic import BaseModel, Field,EmailStr
from typing import Optional
from src.datamodel.database.domain.DigitalSignage import Doctor
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.dbs.getdb import postresql as db

logger = logging.getLogger(__name__)

# ---------- API CONFIG ----------
def api_config():
    config = {
        "path": "",
        "status_code": 201,
        "tags": ["EmergencyInstruction "],
        "summary": "Create EmergencyInstruction ",
        "response_model": dict,
        "description": "Create a new EmergencyInstruction entry",
        "response_description": "Created EmergencyInstruction  data",
        "deprecated": False,
    }
    return ApiConfig(**config)


class DoctorCreate(BaseModel):
    name: str
    specialty: str
    department: str
    phone_number: str
    email: EmailStr
    office_location: str
    availability_hours: str
    bio: Optional[str] = None


async def main(
    request: Request,
    payload: DoctorCreate,   # ✅ Take request model
    db: AsyncSession = Depends(db),
):
    # 1) Validate token
    validate_token_start = time.time()
    validate_token(request)
    entity_uuid=request.state.entity_uuid
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    try:
        exist_id = str(uuid.uuid4())
        # 3) Create EmergencyExit object
        new_exit = Doctor(
            id =exist_id,
            name=payload.name,
            specialty=payload.specialty,
            department=payload.department,
            phone_number=payload.phone_number,
            email=payload.email,
            office_location=payload.office_location,
            availability_hours=payload.availability_hours,
            bio=payload.bio,
            entity_uuid=entity_uuid
        )
        await new_exit.insert()

        logger.info(f"Doctor created successfully: {new_exit.id}")

        # 4) Response
        return {
            "status": "success",
            "message": "Doctor created successfully",
            "data": {
                "id": new_exit.id,
                "name": new_exit.name,
                "specialty": new_exit.specialty,
                "department": new_exit.department,
                "phone_number": new_exit.phone_number,
                "email": new_exit.email,
                "office_location":new_exit.office_location,
                "availability_hours": new_exit.availability_hours,
                "bio": new_exit.bio
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating Doctor : {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Doctor : {str(e)}"
        )
