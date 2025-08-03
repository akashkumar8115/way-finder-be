# from fastapi import HTTPException, Depends, status
# from pydantic import BaseModel, Field
# from typing import Optional, List
# import time
# import logging
# from src.datamodel.database.domain.DigitalSignage import Building, Floor
# from src.datamodel.datavalidation.apiconfig import ApiConfig


# logger = logging.getLogger(__name__)


# def api_config():
#     config = {
#         "path": "/with-floors",
#         "status_code": 201,
#         "tags": ["Building"],
#         "summary": "Create Building with Floors",
#         "response_model": dict,
#         "description": "Create a new building with multiple floors in one request.",
#         "response_description": "Created building and floors data",
#         "deprecated": False,
#     }
#     return ApiConfig(**config)


# class FloorCreateData(BaseModel):
#     label: str = Field(..., description="Name/label of the floor")
#     order: int = Field(..., description="Floor order/number")
#     imageUrl: Optional[str] = Field(None, description="Floor plan image URL or base64")

#     class Config:
#         allow_population_by_field_name = True


# class BuildingWithFloorsRequest(BaseModel):
#     name: str = Field(..., description="Name of the building")
#     address: Optional[str] = Field(None, description="Building address")
#     description: Optional[str] = Field(None, description="Description of the building")
#     floors: List[FloorCreateData] = Field(default=[], description="List of floors to create")

#     class Config:
#         allow_population_by_field_name = True


# class FloorResponseData(BaseModel):
#     floor_id: str
#     label: str
#     order: int
#     imageUrl: Optional[str] = None
#     createdAt: str

#     class Config:
#         allow_population_by_field_name = True


# class BuildingWithFloorsResponse(BaseModel):
#     building_id: str = Field(alias="id")
#     name: str
#     address: Optional[str] = None
#     description: Optional[str] = None
#     floors: List[FloorResponseData] = []
#     createdAt: str

#     class Config:
#         allow_population_by_field_name = True


# async def main(
#     building_data: BuildingWithFloorsRequest,
# ):
#     try:
#         # Check if building with same name exists
#         existing_building = await Building.find_one({
#             "name": building_data.name,
#             "status": "active"
#         })
        
#         if existing_building:
#             raise HTTPException(
#                 status_code=status.HTTP_409_CONFLICT,
#                 detail=f"Building with name '{building_data.name}' already exists"
#             )

#         # Create new building
#         new_building = Building(
#             name=building_data.name,
#             address=building_data.address,
#             description=building_data.description,
#             floors=[],
#             datetime=time.time(),
#             status="active"
#         )

#         # Save building to database
#         await new_building.insert()
        
#         created_floors = []
#         floor_ids = []

#         # Create floors if provided
#         for floor_data in building_data.floors:
#             # Check if floor order already exists
#             existing_floor = await Floor.find_one({
#                 "floor_number": floor_data.order,
#                 "building_id": new_building.building_id,
#                 "status": "active"
#             })
            
#             if existing_floor:
#                 logger.warning(f"Floor with order {floor_data.order} already exists, skipping")
#                 continue

#             new_floor = Floor(
#                 name=floor_data.label,
#                 building_id=new_building.building_id,
#                 floor_number=floor_data.order,
#                 floor_plan_url=floor_data.imageUrl,
#                 locations=[],
#                 datetime=time.time(),
#                 status="active"
#             )

#             await new_floor.insert()
#             floor_ids.append(new_floor.floor_id)
            
#             created_floors.append(FloorResponseData(
#                 floor_id=new_floor.floor_id,
#                 label=new_floor.name,
#                 order=new_floor.floor_number,
#                 imageUrl=new_floor.floor_plan_url,
#                 createdAt=time.strftime('%Y-%m-%dT%H:%M:%S.%fZ', time.gmtime(new_floor.datetime))
#             ))

#         # Update building with floor IDs
#         new_building.floors = floor_ids
#         new_building.update_on = time.time()
#         await new_building.save()
        
#         logger.info(f"Building with floors created successfully: {new_building.building_id}")

#         # Prepare response
#         response = BuildingWithFloorsResponse(
#             id=new_building.building_id,
#             name=new_building.name,
#             address=new_building.address,
#             description=new_building.description,
#             floors=created_floors,
#             createdAt=time.strftime('%Y-%m-%dT%H:%M:%S.%fZ', time.gmtime(new_building.datetime))
#         )

#         return {
#             "status": "success",
#             "message": "Building with floors created successfully",
#             "data": response
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception(f"Error creating building with floors: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to create building with floors: {str(e)}"
#         )






from fastapi import HTTPException, Depends, status, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import time
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from src.datamodel.database.domain.DigitalSignage import Building
from src.datamodel.datavalidation.apiconfig import ApiConfig
from src.core.middleware.token_validate_middleware import validate_token
from src.core.database.dbs.getdb import postresql as db


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 201,
        "tags": ["Building"],
        "summary": "Create Building",
        "response_model": dict,
        "description": "Create a new building for the way-finder system.",
        "response_description": "Created building data",
        "deprecated": False,
    }
    return ApiConfig(**config)


class BuildingCreateRequest(BaseModel):
    name: str = Field(..., description="Name of the building")
    address: Optional[str] = Field(None, description="Building address")
    description: Optional[str] = Field(None, description="Description of the building")

    class Config:
        allow_population_by_field_name = True


class BuildingResponse(BaseModel):
    building_id: str
    name: str
    address: Optional[str] = None
    floors: List[str] = []
    description: Optional[str] = None
    entity_uuid: Optional[str] = None
    # created_by: Optional[str] = None
    datetime: float
    status: str

    class Config:
        allow_population_by_field_name = True


async def main(
    request: Request,    
    building_data: BuildingCreateRequest,
    db: AsyncSession = Depends(db)
):
    
    """Main handler for content uploads"""
    # Validate token and get user info
    validate_token_start = time.time()
    validate_token(request)
    entity_uuid = request.state.entity_uuid
    user_uuid = request.state.user_uuid
    validate_token_time = time.time() - validate_token_start
    logger.info(f"PERFORMANCE: Token validation took {validate_token_time:.4f} seconds")

    try:
        # Check if building with same name exists
        existing_building = await Building.find_one({
            "name": building_data.name,
            "entity_uuid": entity_uuid,
            "status": "active"
        })
        
        if existing_building:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Building with name '{building_data.name}' already exists"
            )

        # Create new building
        new_building = Building(
            name=building_data.name,
            address=building_data.address,
            description=building_data.description,
            entity_uuid=entity_uuid,
            floors=[],  # Empty list initially
            datetime=time.time(),
            status="active"
        )

        # Save to database
        await new_building.insert()
        
        logger.info(f"Building created successfully: {new_building.building_id}")

        # Prepare response
        response = BuildingResponse(
            building_id=new_building.building_id,
            name=new_building.name,
            address=new_building.address,
            floors=new_building.floors,
            entity_uuid=entity_uuid,
            description=new_building.description,
            datetime=new_building.datetime,
            status=new_building.status
        )

        return {
            "status": "success",
            "message": "Building created successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating building: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create building: {str(e)}"
        )


