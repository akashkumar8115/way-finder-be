from pydantic import BaseModel

class InferenceModelRequest(BaseModel):
    query: str
    collection_path: str
    n_results:int