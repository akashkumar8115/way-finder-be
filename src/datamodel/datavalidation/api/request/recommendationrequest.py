from pydantic import BaseModel

class RecommendationRequest(BaseModel):
    id: int
