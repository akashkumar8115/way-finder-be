from fastapi import HTTPException, Depends, Request, status,Form ,File,UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import logging
from typing import Dict
from typing import Optional
from src.datamodel.database.domain.DigitalSignage import Event
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.authentication.authentication import get_current_user, get_token_payload
from src.datamodel.database.userauth.AuthenticationTables import  User
from src.core.database.dbs.getdb import postresql as db
from src.services.permit.permit_service import PermitService
from sqlalchemy import select
from src.core.database.dbs.getdb import postresql as db
from fastapi.encoders import jsonable_encoder
import base64
import os
import json

from b2sdk.v2 import InMemoryAccountInfo, B2Api
logger = logging.getLogger(__name__)
permit_service = PermitService()


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["event"],
        "summary": "Update event data",
        "response_model": None,
        "description": "This API endpoint updates an existing event in the database.",
        "response_description": "Details of the updated entity.",
        "deprecated": False,
    }
    return ApiConfig(**config)
def upload_image_to_b2(file_data: dict, base64_image: str) -> dict:
    """
    Uploads an image to Backblaze B2 and returns metadata for MongoDB.

    Args:
        file_data (dict): File metadata (name, size, type).
            Example: { "name": "20250712172424_ccc80a85.png", "size": 206601, "type": "image/png" }
        base64_image (str): Base64 string of the image. Must be "data:image/png;base64,...."

    Returns:
        dict: Metadata including B2 URL, name, size, type.
    """
    if not base64_image:
        raise ValueError("No image data provided")

    # Environment variables
    B2_ACCOUNT_ID = os.getenv("B2_KEY_ID")
    B2_APPLICATION_KEY = os.getenv("B2_APP_KEY")
    B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")

    # Ensure correct base64 format
    if "," in base64_image:
        _, encoded = base64_image.split(",", 1)
    else:
        encoded = base64_image

    # Fix base64 padding (must be multiple of 4)
    missing_padding = len(encoded) % 4
    if missing_padding:
        encoded += "=" * (4 - missing_padding)

    try:
        file_bytes = base64.b64decode(encoded)
    except Exception as e:
        raise ValueError(f"Invalid base64 data: {str(e)}")

    # Connect to Backblaze
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", B2_ACCOUNT_ID, B2_APPLICATION_KEY)
    bucket = b2_api.get_bucket_by_name(B2_BUCKET_NAME)

    # Upload using the original file name
    headers = {
    "Content-Type": file_data.content_type or "image/png"
}
    bucket.upload_bytes(
       file_bytes,
       file_data.filename,
       content_type=headers["Content-Type"]
    )

    # Create public URL
    url = f"https://{B2_BUCKET_NAME}.s3.eu-central-003.backblazeb2.com/{file_data.filename}"

    # Return object to store in MongoDB
    return {
        "name": file_data.filename,
        "size": file_data.size,
        "type": file_data.content_type,
        "url": url
    }
async def update_event_in_db(
    entity_uuid: str,
    name: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    description: Optional[str],
    is_published: Optional[bool],
    metadata: Optional[str],
    image_base64: Optional[dict],
    current_user: User
):
    try:
        # Fetch the existing event
        existing_event = await Event.find_one(Event.event_id == entity_uuid)
        if not existing_event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Update fields only if provided
        if name is not None:
            existing_event.name = name
        if start_date is not None:
            existing_event.start_date = start_date
        if end_date is not None:
            existing_event.end_date = end_date
        if description is not None:
            existing_event.description = description
        if is_published is not None:
            existing_event.is_published = is_published in ["true", "True", True]
        if metadata is not None:
            existing_event.metadata = metadata
        if image_base64 is not None:
            existing_event.image_url = image_base64["url"]

        existing_event.updated_by = current_user

        # Save updates
        await existing_event.save()
        return {"message": "Event updated successfully", "event_id": entity_uuid}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



async def main( request: Request,
    entity_uuid: str,
    name: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_published: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
):
    # Parse metadata
    try:
        metadata_dict = json.loads(metadata) if metadata else None
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid metadata JSON")

    image_base64 = None
    if image_file:
        content = await image_file.read()
        base64_image = f"data:{image_file.content_type};base64,{base64.b64encode(content).decode()}"
        image_base64 = upload_image_to_b2(image_file, base64_image)

    return await update_event_in_db(
        entity_uuid=entity_uuid,
        name=name,
        start_date=start_date,
        end_date=end_date,
        description=description,
        is_published=is_published,
        metadata=metadata_dict,
        image_base64=image_base64,
        current_user="shamimahmadupup1"
    )