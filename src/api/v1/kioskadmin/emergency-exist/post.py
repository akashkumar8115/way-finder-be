from fastapi import HTTPException, Depends, status, Request
import time
import logging
import uuid
from pydantic import BaseModel, Field
from typing import Optional
from src.datamodel.database.domain.DigitalSignage import EmergencyExit
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

class EmergencyExitCreateRequest(BaseModel):
    name: str = Field(..., description="Exit name")
    description: Optional[str] = Field(None, description="Exit description")
    direction_instructions: Optional[str] = Field(None, description="Direction instructions")
    distance_meters: Optional[int] = Field(None, description="Distance in meters")
    estimated_time_minutes: Optional[int] = Field(None, description="Estimated time in minutes")
    is_primary_exit: bool = Field(False, description="Is this the primary exit?")
    floor_location: Optional[str] = Field(None, description="Floor or location info")
    is_active: bool = Field(True, description="Is this exit active?")
    display_order: int = Field(0, description="Display order for sorting")

# ---------- CREATE HANDLER ----------
async def main(
    request: Request,
    payload: EmergencyExitCreateRequest,   # ✅ Take request model
    db: AsyncSession = Depends(db),
):
    # 1) Validate token
    validate_token_start = time.time()
    validate_token(request)
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    try:
        # 2) Duplicate check (by name for this entity)
        existing = await EmergencyExit.find_one(
            EmergencyExit.name == payload.name
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Emergency exit with name '{payload.name}' already exists"
            )
        exist_id = str(uuid.uuid4())
        # 3) Create EmergencyExit object
        new_exit = EmergencyExit(
            id =exist_id,
            name=payload.name,
            description=payload.description,
            direction_instructions=payload.direction_instructions,
            distance_meters=payload.distance_meters,
            estimated_time_minutes=payload.estimated_time_minutes,
            is_primary_exit=payload.is_primary_exit,
            floor_location=payload.floor_location,
            is_active=payload.is_active,
            display_order=payload.display_order,
        )
        await new_exit.insert()

        logger.info(f"EmergencyExit created successfully: {new_exit.id}")

        # 4) Response
        return {
            "status": "success",
            "message": "Emergency exit created successfully",
            "data": {
                "id": new_exit.id,
                "name": new_exit.name,
                "description": new_exit.description,
                "direction_instructions": new_exit.direction_instructions,
                "distance_meters": new_exit.distance_meters,
                "estimated_time_minutes": new_exit.estimated_time_minutes,
                "is_primary_exit": new_exit.is_primary_exit,
                "floor_location": new_exit.floor_location,
                "is_active": new_exit.is_active,
                "display_order": new_exit.display_order,
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
