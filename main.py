import os
import uvicorn
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.core.configsetup.appconfig import LoadConfig
from src.core.configsetup.directorysetup import DirectorySetup
from src.core.routerbuilder.createroute import RouteBuilder
from src.core.authentication.thirdparty_auth import thirdparty_route
from src.core.authentication.validate_token import validate_token
from src.core.authentication.password_auth import password_auth
from src.core.authentication.logout import logout_route
from src.datamodel.database.Base import Base
import src.datamodel.database.userauth.AuthenticationTables
import src.datamodel.database.domain.AppTables
import src.datamodel.database.domain.Purchase
# import src.datamodel.database.UserLog
from src.core.database.dbs.postgresql.connect import engine
from src.core.database.dbs.mongodb.connect import init_db, check_db_connection
import asyncio
import asyncpg


# Initialize logging 
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

load_dotenv()

description = """
Example API to demonstrate SSO login in FastAPI
"""

# Load configuration
config = LoadConfig()
config_load = config.load_config(Path("./config.yaml"))


# Setup and clean up
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Replicating directories for data models and testing
        replicate_api_path = DirectorySetup(
            config_load.replicate_dir.replicate_from,
            config_load.replicate_dir.replicate_to,
        )
        replicate_api_path.read_dir_structure()

        # Creating data database assets
        # Base.metadata.create_all(bind=engine, checkfirst=True)
        
        # Async table creation for PostgreSQL
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)

        # Initialize MongoDB Beanie
        logger.info("Initializing MongoDB")
        await check_db_connection()
        await init_db()
        yield
    except Exception as err:
        logger.error(f"Lifespan setup error: {err}")
        raise


# Initialize FastAPI app
app = FastAPI(
    title=os.getenv("ORG_NAME"), description=description, version="1.0.0", lifespan=lifespan
)

origins = os.getenv("ORIGIN_URL").split(",")  

# origins  = ["*"]


# Add middleware
app.add_middleware(SessionMiddleware, secret_key="!secret")
app.add_middleware(
    CORSMiddleware, 
    allow_origins = origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"]
)

logger.info("Allow origins: %s", origins)

# Initialize API directory
logger.info("Initializing Routes")
route_initializer = RouteBuilder(Path(config_load.api_details.api_path))

# Build routes dynamically based on directory structure
logger.debug("Adding routes ")
routes = route_initializer.router_config()

# Load OAuth route
# app.include_router(thirdparty_route)
app.include_router(password_auth)
app.include_router(logout_route)
app.include_router(validate_token)

# Load routes to FastAPI router
app.include_router(routes)




# Ensure storage directory exists
# os.makedirs(settings.SHARED_STORAGE_PATH, exist_ok=True)

# # Mount static files
# app.mount("/storage", StaticFiles(directory=settings.SHARED_STORAGE_PATH), name="storage")




if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config_load.app_details.host_address,
        port=config_load.app_details.port,
    )