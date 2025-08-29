

from fastapi import HTTPException, Depends, Request, status,Path
import logging
from bson import ObjectId
import asyncio
from typing import Dict, List
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.authentication.authentication import get_current_user, get_token_payload
from src.datamodel.database.userauth.AuthenticationTables import Entity, Role, User, UserEntityRoleMap
from sqlalchemy.exc import IntegrityError
from src.core.database.dbs.getdb import postresql as db
from sqlalchemy.orm import Session
from src.datamodel.database.domain.DigitalSignage import Event
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.permit.permit_service import PermitService
from sqlalchemy import select
import time
from src.core.middleware.token_validate_middleware import validate_token
from datetime import datetime

logger = logging.getLogger(__name__)
permit_service = PermitService()

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["event"],
        "summary": "Delete event",
        "response_model": None,
        "description": "This API endpoint deletes an event and its associated users and role mappings.",
        "response_description": "Details of the deletion operation.",
        "deprecated": False,
    }
    return ApiConfig(**config)

async def delete_event_in_db(id: str):
    try:
        event = await Event.find_one(Event.event_id == id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        await event.delete()

        return {"message": "Event deleted successfully", "event_id": id}
    except Exception as e:
        logger.error(f"Error deleting event {id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting event: {str(e)}")

async def main(id: str, db: AsyncSession = Depends(db)):
    
    return await delete_event_in_db(id)
