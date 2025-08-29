from fastapi import HTTPException, Depends, status, Form, Request
from typing import Optional
import time
import logging
import uuid

from src.datamodel.database.domain.DigitalSignage import EmergencyAlert
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
        "tags": ["Emergency Alert"],
        "summary": "Create Emergency Alert",
        "response_model": dict,
        "description": "Create a new emergency alert entry",
        "response_description": "Created emergency alert data",
        "deprecated": False,
    }
    return ApiConfig(**config)


# ---------- CREATE HANDLER ----------
async def main(
    request: Request,
    title: str = Form(..., description="Alert title"),
    alert_type: str = Form(..., description="Alert type (info, warning, danger)"),
    message: Optional[str] = Form(None, description="Alert message"),
    is_active: bool = Form(True, description="Is alert active?"),
    start_time: Optional[str] = Form(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Form(None, description="End time (ISO format)"),
    db: AsyncSession = Depends(db),
):
    # 1) Validate token & capture entity
    validate_token_start = time.time()
    validate_token(request)
    entity_uuid = request.state.entity_uuid
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    try:
        # 2) Duplicate checks
        existing_by_title = await EmergencyAlert.find_one({
            "title": title,
            "entity_uuid": entity_uuid,
            "status": "active"
        })
        if existing_by_title:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Emergency alert with title '{title}' already exists"
            )

        existing_by_type = await EmergencyAlert.find_one({
            "alert_type": alert_type,
            "entity_uuid": entity_uuid,
            "status": "active"
        })
        if existing_by_type:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Emergency alert with type '{alert_type}' already exists"
            )

        # 3) Generate UUID and insert
        alert_id = str(uuid.uuid4())
        new_alert = EmergencyAlert(
            alert_id=alert_id,
            title=title,
            message=message,
            alert_type=alert_type,
            is_active=is_active,
            start_time=start_time,
            end_time=end_time,
            entity_uuid=entity_uuid,
            status="active"
        )
        await new_alert.insert()

        logger.info(f"Emergency alert created successfully: {alert_id}")

        # 4) Simple dict response
        return {
            "status": "success",
            "message": "Emergency alert created successfully",
            "data": {
                "alert_id": new_alert.alert_id,
                "title": new_alert.title,
                "message": new_alert.message,
                "alert_type": new_alert.alert_type,
                "is_active": new_alert.is_active,
                "start_time": new_alert.start_time,
                "end_time": new_alert.end_time,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating emergency alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create emergency alert: {str(e)}"
        )
