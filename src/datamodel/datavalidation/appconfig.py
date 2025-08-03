from pydantic import BaseModel, DirectoryPath
from pydantic_settings import BaseSettings
from typing import List


# Application level Config data model
class ApplicationDetails(BaseModel):
    title: str
    version: str
    host_address: str
    port: int

class Postgresql(BaseSettings):
    host: str
    port: int
    username: str
    password: str
    database_name: str
    DATABASE_URL: str

class DatabaseConfig(BaseSettings):
    postgresql: Postgresql


class ApiDetails(BaseModel):
    api_path: DirectoryPath

class ReplicateDir(BaseModel):
    replicate_from: DirectoryPath
    replicate_to: List[str]


class ApplicationConfig(BaseSettings):
    app_details: ApplicationDetails
    database_config: DatabaseConfig
    api_details: ApiDetails
    replicate_dir: ReplicateDir