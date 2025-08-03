from fastapi import HTTPException, Body
from pydantic import BaseModel
from typing import List
import logging
from pydantic import BaseModel
from src.datamodel.database.domain.DigitalSignage import Screens
from src.datamodel.datavalidation.apiconfig import ApiConfig

logger = logging.getLogger(__name__)


async def screenStateModify(screen_ids: List[str]):
    try:
        # Query the database for the screens with the given screen_ids
        screens = await Screens.find({"screen_id": {"$in": screen_ids}}).to_list()
        if not screens:
            return {"message": "Screens not found with the provided IDs"}

        # Update the screenStateModified field for each screen
        for screen in screens:
            screen.screenStateModified = True
            await screen.save()

        return {"message": "ScreenStateModified updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


