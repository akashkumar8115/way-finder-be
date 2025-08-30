from fastapi import HTTPException, Depends, status, Request
import time
import logging
import uuid
from pydantic import BaseModel, Field,EmailStr
from typing import Optional
from src.datamodel.database.domain.DigitalSignage import DailyAnnouncement
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.dbs.getdb import postresql as db
from datetime import date

logger = logging.getLogger(__name__)

# ---------- API CONFIG ----------
def api_config():
    config = {
        "path": "",
        "status_code": 201,
        "tags": ["DailyAnnouncement "],
        "summary": "Create DailyAnnouncement ",
        "response_model": dict,
        "description": "Create a new DailyAnnouncement entry",
        "response_description": "Created DailyAnnouncement  data",
        "deprecated": False,
    }
    return ApiConfig(**config)

class DailyAnnouncementUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, description="Title of the announcement")
    content: Optional[str] = Field(None, description="Content of the announcement")
    priority_level: Optional[int] = Field(None, description="Priority level (e.g., 1=High, 2=Medium, 3=Low)")
    active: Optional[bool] = Field(None, description="Whether the announcement is active")
    display_date: Optional[date] = Field(None, description="Date when the announcement should be displayed")


async def main(
    request: Request,
    payload: DailyAnnouncementUpdateRequest,   # ✅ Take request model
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
        new_exit = DailyAnnouncement(
            id =exist_id,
            title=payload.title,
            content=payload.content,
            priority_level=payload.priority_level,
            active=payload.active,
            display_date=payload.display_date,
            entity_uuid=entity_uuid
        )
        await new_exit.insert()

        logger.info(f"DailyAnnouncement created successfully: {new_exit.id}")

        # 4) Response
        return {
            "status": "success",
            "message": "DailyAnnouncement created successfully",
            "data": {
                "id": new_exit.id,
                "title": new_exit.title,
                "content": new_exit.content,
                "priority_level": new_exit.priority_level,
                "active": new_exit.active,
                "display_date": new_exit.display_date
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
