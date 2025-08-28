from fastapi import HTTPException, Depends, status, Request
import time
import logging
import uuid
from pydantic import BaseModel, Field
from typing import Optional
from src.datamodel.database.domain.DigitalSignage import NonEmergencyContact
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
        "tags": ["Emergency Exit"],
        "summary": "Create Emergency Exit",
        "response_model": dict,
        "description": "Create a new emergency exit entry",
        "response_description": "Created emergency exit data",
        "deprecated": False,
    }
    return ApiConfig(**config)


class NonEmergencyContactCreateRequest(BaseModel):
    name: str = Field(..., description="Contact name")
    description: Optional[str] = Field(None, description="Description of the contact")
    phone_number: Optional[str] = Field(None, description="Phone number")
    department: Optional[str] = Field(None, description="Department name")
    is_active: bool = Field(True, description="Is this contact active?")
    display_order: int = Field(0, description="Display order for sorting")
    icon_name: str = Field("phone", description="Associated icon name")

# ---------- CREATE HANDLER ----------
async def main(
    request: Request,
    payload: NonEmergencyContactCreateRequest,   # ✅ Take request model
    db: AsyncSession = Depends(db),
):
    # 1) Validate token
    validate_token_start = time.time()
    validate_token(request)
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    try:
        # 2) Duplicate check (by name for this entity)
        existing = await NonEmergencyContact.find_one(
            NonEmergencyContact.name == payload.name
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"NonEmergencyContact exit with name '{payload.name}' already exists"
            )
        exist_id = str(uuid.uuid4())
        # 3) Create EmergencyExit object
        new_exit = NonEmergencyContact(
            id =exist_id,
            name=payload.name,
            description=payload.description,
            phone_number=payload.phone_number,
            department=payload.department,
            is_active=payload.is_active,
            display_order=payload.display_order,
            icon_name=payload.icon_name
            
        )
        await new_exit.insert()

        logger.info(f"NonEmergencyContact created successfully: {new_exit.id}")

        # 4) Response
        return {
            "status": "success",
            "message": "NonEmergencyContact exit created successfully",
            "data": {
                "id": new_exit.id,
                "name": new_exit.name,
                "description": new_exit.description,
                "phone_number": new_exit.phone_number,
                "department": new_exit.department,
                "is_active": new_exit.is_active,
                "display_order": new_exit.display_order,
                "icon_name":payload.icon_name
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating emergency exit: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create emergency exit: {str(e)}"
        )
