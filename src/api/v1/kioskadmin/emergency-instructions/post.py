from fastapi import HTTPException, Depends, status, Request
import time
import logging
import uuid
from pydantic import BaseModel, Field
from typing import Optional
from src.datamodel.database.domain.DigitalSignage import EmergencyInstruction
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


class EmergencyInstructionCreateRequest(BaseModel):
    instruction_type: str = Field(..., description="Instruction type")
    title: str = Field(..., description="Title of the instruction")
    content: str = Field(..., description="Content of the instruction")
    priority_level: int = Field(1, description="Priority")
    is_active: bool = Field(True, description="Is active")

# ---------- CREATE HANDLER ----------
async def main(
    request: Request,
    payload: EmergencyInstructionCreateRequest,   # ✅ Take request model
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
        new_exit = EmergencyInstruction(
            id =exist_id,
            instruction_type=payload.instruction_type,
            title=payload.title,
            content=payload.content,
            priority_level=payload.priority_level,
            is_active=payload.is_active
        )
        await new_exit.insert()

        logger.info(f"EmergencyInstruction created successfully: {new_exit.id}")

        # 4) Response
        return {
            "status": "success",
            "message": "EmergencyInstruction created successfully",
            "data": {
                "id": new_exit.id,
                "instruction_type": new_exit.instruction_type,
                "title": new_exit.title,
                "priority_level": new_exit.priority_level,
                "content": new_exit.content,
                "is_active": new_exit.is_active
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating EmergencyInstruction : {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create emergEmergencyInstructionency : {str(e)}"
        )
