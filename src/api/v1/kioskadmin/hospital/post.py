from fastapi import HTTPException, Depends, status, Request
import time
import logging
import uuid
from pydantic import BaseModel, Field,EmailStr
from typing import Optional
from src.datamodel.database.domain.DigitalSignage import HospitalService
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
        "tags": ["HospitalService "],
        "summary": "Create HospitalService ",
        "response_model": dict,
        "description": "Create a new HospitalService entry",
        "response_description": "Created HospitalService  data",
        "deprecated": False,
    }
    return ApiConfig(**config)


class HospitalServiceRequest(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    location: str
    phone_number: str
    hours: str
    requirements: Optional[str] = None


async def main(
    request: Request,
    payload: HospitalServiceRequest,   # ✅ Take request model
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
        new_exit = HospitalService(
            id =exist_id,
            name=payload.name,
            description=payload.description,
            category=payload.category,
            phone_number=payload.phone_number,
            location=payload.location,
            hours=payload.hours,
            requirements=payload.requirements,
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
                "description": new_exit.description,
                "category": new_exit.category,
                "phone_number": new_exit.phone_number,
                "location": new_exit.location,
                "hours":new_exit.hours,
                "requirements": new_exit.requirements
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating HospitalService : {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create HospitalService : {str(e)}"
        )
