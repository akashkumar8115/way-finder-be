from fastapi import HTTPException, Path as FastAPIPath, Query, status
from typing import Optional
import time
import logging
from src.datamodel.database.domain.DigitalSignage import VerticalConnector, Floor
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)

def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Vertical Connector"],
        "summary": "Delete Vertical Connector",
        "response_model": dict,
        "description": "Delete a vertical connector by marking it as inactive.",
        "response_description": "Deletion confirmation",
        "deprecated": False,
    }
    return ApiConfig(**config)

async def main(
    connector_id: str = FastAPIPath(..., description="Vertical connector ID to delete"),
    deleted_by: Optional[str] = Query(None, description="User who deleted the connector")
):
    try:
        # Find the connector
        existing_connector = await VerticalConnector.find_one({
            "connector_id": connector_id,
            "status": "active"
        })
        
        if not existing_connector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vertical connector with ID '{connector_id}' not found"
            )

        # Mark connector as inactive (soft delete)
        existing_connector.status = "inactive"
        existing_connector.updated_by = deleted_by
        existing_connector.update_on = time.time()
        
        await existing_connector.save()
        
        # Remove connector from floor's vertical_connectors list
        try:
            floor = await Floor.find_one({
                "floor_id": existing_connector.floor_id,
                "status": "active"
            })
            
            if floor and connector_id in floor.vertical_connectors:
                floor.vertical_connectors.remove(connector_id)
                floor.updated_by = deleted_by
                floor.update_on = time.time()
                await floor.save()
                logger.info(f"Removed connector {connector_id} from floor {existing_connector.floor_id}")
        
        except Exception as floor_update_error:
            logger.warning(f"Failed to update floor vertical_connectors list: {str(floor_update_error)}")
            # Don't fail the deletion if floor update fails
        
        logger.info(f"Vertical connector deleted successfully: {connector_id}")

        return {
            "status": "success",
            "message": "Vertical connector deleted successfully",
            "data": {
                "connector_id": connector_id,
                "name": existing_connector.name,
                "shared_id": existing_connector.shared_id,
                "floor_id": existing_connector.floor_id,
                "deleted_at": existing_connector.update_on,
                "deleted_by": deleted_by
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting vertical connector: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete vertical connector: {str(e)}"
        )
