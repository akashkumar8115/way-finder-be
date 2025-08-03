from fastapi import HTTPException, Depends, status, UploadFile, File, Form, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import time
import logging
from src.datamodel.database.domain.DigitalSignage import Floor, Building
from src.datamodel.datavalidation.apiconfig import ApiConfig
# from src.services.files.minio_service import minio_service
from src.services.files.backblaze import b2_service
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 201,
        "tags": ["Floor"],
        "summary": "Create Floor",
        "response_model": dict,
        "description": "Create a new floor for a building in the way-finder system with optional floor plan image upload.",
        "response_description": "Created floor data",
        "deprecated": False,
    }
    return ApiConfig(**config)


class FloorCreateRequest(BaseModel):
    name: str = Field(..., description="Name/label of the floor (e.g., 'Ground Floor', 'First', 'Second')")
    building_id: str = Field(..., description="Building ID this floor belongs to")
    floor_number: int = Field(..., description="Floor number/order")
    description: Optional[str] = Field(None, description="Description of the floor")
    is_published: bool = Field(default=True, description="Whether floor is published")

    class Config:
        allow_population_by_field_name = True


class FloorResponse(BaseModel):
    floor_id: str
    name: str
    building_id: str
    floor_number: int
    floor_plan_url: Optional[str] = Field(None, alias="imageUrl")
    floor_plan_info: Optional[dict] = Field(None, description="Information about uploaded floor plan")
    locations: List[str] = []
    vertical_connectors: List[str] = []
    paths: List[str] = []
    is_published: bool
    description: Optional[str] = None
    entity_uuid: Optional[str] = None
    datetime: float
    status: str

    class Config:
        allow_population_by_field_name = True


async def main(
    request: Request,
    name: str = Form(..., description="Name/label of the floor"),
    building_id: str = Form(..., description="Building ID this floor belongs to"),
    floor_number: int = Form(..., description="Floor number/order"),
    description: Optional[str] = Form(None, description="Description of the floor"),
    is_published: bool = Form(True, description="Whether floor is published"),
    floor_plan: Optional[UploadFile] = File(None, description="Floor plan image file (PNG, JPG, JPEG, GIF)"),
    db: AsyncSession = Depends(db),
):
    # Get entity_uuid from request
    validate_token_start = time.time()
    
    validate_token(request)
    
    entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    """
    Create a new floor with optional floor plan image upload
    """
    try:
        # Create floor data object for validation
        floor_data = FloorCreateRequest(
            name=name,
            building_id=building_id,
            floor_number=floor_number,
            description=description,
            is_published=is_published
        )
        
        # Check if building exists
        building = await Building.find_one({
            "building_id": building_id,
            "entity_uuid": entity_uuid,
        })
        
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building with ID '{building_id}' not found"
            )

        # Check if floor with same name exists in the same building
        existing_floor = await Floor.find_one({
            "name": name,
            "building_id": building_id,
            "status": "active"
        })
        
        if existing_floor:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Floor with name '{name}' already exists in this building"
            )

        # Check if floor number already exists in the same building
        existing_floor_number = await Floor.find_one({
            "floor_number": floor_number,
            "building_id": building_id,
            "status": "active"
        })
        
        if existing_floor_number:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Floor number '{floor_number}' already exists in this building"
            )

        # Create new floor first (to get floor_id for file upload)
        new_floor = Floor(
            name=name,
            building_id=building_id,
            floor_number=floor_number,
            description=description,
            locations=[],
            vertical_connectors=[],
            paths=[],
            is_published=is_published,
            entity_uuid=entity_uuid,
            datetime=time.time(),
            status="active"
        )

        # Save floor to database to get the floor_id
        await new_floor.insert()
        
        floor_plan_url = None
        floor_plan_info = None
        
        # Handle floor plan upload if provided - CHANGED TO USE MINIO
        if floor_plan:
            try:
                # Replace Wasabi service with MinIO service
                upload_result = await b2_service.upload_floor_plan(
                    file=floor_plan,
                    floor_id=new_floor.floor_id,
                    building_id=building_id
                )
                
                if upload_result["success"]:
                    floor_plan_url = upload_result["file_url"]
                    floor_plan_info = {
                        "filename": upload_result["filename"],
                        "original_filename": upload_result["original_filename"],
                        "file_size": upload_result["file_size"],
                        "dimensions": upload_result.get("dimensions"),
                        "content_type": upload_result["content_type"]
                    }
                    
                    # Update floor with the floor plan URL
                    new_floor.floor_plan_url = floor_plan_url
                    await new_floor.save()
                    
                    logger.info(f"Floor plan uploaded successfully to MinIO for floor: {new_floor.floor_id}")
                else:
                    # Upload failed, but don't fail the floor creation
                    logger.warning(f"Floor plan upload to MinIO failed: {upload_result.get('error', 'Unknown error')}")
                    floor_plan_info = {
                        "upload_error": upload_result.get('error', 'Upload failed'),
                        "message": "Floor created successfully, but floor plan upload failed"
                    }
                
            except Exception as upload_error:
                # Log the error but don't fail the floor creation
                logger.error(f"Floor plan upload to MinIO failed for floor {new_floor.floor_id}: {str(upload_error)}")
                floor_plan_info = {
                    "upload_error": f"Floor plan upload failed: {str(upload_error)}",
                    "message": "Floor created successfully, but floor plan upload failed"
                }
        
        # Update building's floors list
        if new_floor.floor_id not in building.floors:
            building.floors.append(new_floor.floor_id)
            building.updated_by = None
            building.update_on = time.time()
            await building.save()
        
        logger.info(f"Floor created successfully: {new_floor.floor_id}")

        # Prepare response
        response = FloorResponse(
            floor_id=new_floor.floor_id,
            name=new_floor.name,
            building_id=new_floor.building_id,
            floor_number=new_floor.floor_number,
            floor_plan_url=floor_plan_url,
            floor_plan_info=floor_plan_info,
            locations=new_floor.locations,
            vertical_connectors=new_floor.vertical_connectors, 
            paths=new_floor.paths,
            is_published=new_floor.is_published,
            entity_uuid=entity_uuid,
            description=new_floor.description,
            datetime=new_floor.datetime,
            status=new_floor.status
        )

        # Create success message based on upload status
        success_message = "Floor created successfully"
        if floor_plan_url:
            success_message += " with floor plan uploaded to MinIO"
        elif floor_plan and floor_plan_info and "upload_error" in floor_plan_info:
            success_message += " (floor plan upload to MinIO failed)"

        return {
            "status": "success",
            "message": success_message,
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating floor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create floor: {str(e)}"
        )
