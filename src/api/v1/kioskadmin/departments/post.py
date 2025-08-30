from fastapi import HTTPException, Depends, status, Request
import time
import logging
import uuid
from pydantic import BaseModel, Field,EmailStr
from typing import Optional, List
from src.datamodel.database.domain.DigitalSignage import Department
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
        "tags": ["Department "],
        "summary": "Create Department ",
        "response_model": dict,
        "description": "Create a new Department entry",
        "response_description": "Created Department  data",
        "deprecated": False,
    }
    return ApiConfig(**config)



class DepartmentRequest(BaseModel):
    name: str = Field(..., description="Department name")
    description: Optional[str] = Field(None, description="Department description")
    location: Optional[str] = Field(None, description="Department location in hospital")
    phone_number: str = Field(..., description="Contact number")
    hours: str = Field(..., description="Operating hours")
    services: List[str] = Field(default_factory=list, description="List of services offered")


async def main(
    request: Request,
    payload: DepartmentRequest,   # ✅ Take request model
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
        new_exit = Department(
            id =exist_id,
            name=payload.name,
            description=payload.description,
            phone_number=payload.phone_number,
            location=payload.location,
            hours=payload.hours,
            services=payload.services,
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
                "phone_number": new_exit.phone_number,
                "location":new_exit.location,
                "hours": new_exit.hours,
                "services":new_exit.services
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
