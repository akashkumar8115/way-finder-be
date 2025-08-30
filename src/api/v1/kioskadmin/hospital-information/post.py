from fastapi import HTTPException, Depends, status, Request
import time
import logging
import uuid
from pydantic import BaseModel, Field,EmailStr
from typing import Optional
from src.datamodel.database.domain.DigitalSignage import HospitalInformation
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
        "tags": ["HospitalInformation "],
        "summary": "Create HospitalInformation ",
        "response_model": dict,
        "description": "Create a new HospitalInformation entry",
        "response_description": "Created HospitalInformation  data",
        "deprecated": False,
    }
    return ApiConfig(**config)


class HospitalInformationCreateRequest(BaseModel):
    category_id: str
    category_title: str
    item_title: str
    item_content: str
    item_type: str
    is_important: bool = False
    display_order: int = 0

async def main(
    request: Request,
    payload: HospitalInformationCreateRequest,   # ✅ Take request model
    db: AsyncSession = Depends(db),
):
    # 1) Validate token
    validate_token_start = time.time()
    validate_token(request)
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    try:
        exist_id = str(uuid.uuid4())
        # 3) Create EmergencyExit object
        new_exit = HospitalInformation(
            id =exist_id,
            category_id=payload.category_id or 1,
            category_title=payload.category_title,
            item_title=payload.item_title,
            item_content=payload.item_content,
            item_type=payload.item_type,
            is_important=payload.is_important,
            display_order=payload.display_order
        )
        await new_exit.insert()

        logger.info(f"HospitalInformation created successfully: {new_exit.id}")

        # 4) Response
        return {
            "status": "success",
            "message": "HospitalInformation created successfully",
            "data": {
                "id": new_exit.id,
                "category_id": new_exit.category_id,
                "category_title": new_exit.category_title,
                "item_title": new_exit.item_title,
                "item_content": new_exit.item_content,
                "item_type": new_exit.item_type,
                "is_important":new_exit.is_important,
                "display_order": new_exit.display_order
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating HospitalInformation : {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create HospitalInformation : {str(e)}"
        )
