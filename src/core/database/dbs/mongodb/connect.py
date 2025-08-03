import os
from beanie import init_beanie
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from src.datamodel.database.domain.DigitalSignage import Location, Floor, Building, VerticalConnector, Path, Event
import logging
# Load environment variables
load_dotenv()
# Initialize logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# MongoDB connection details
MONGO_DATABASE_URL = os.getenv("MONGO_DATABASE_URL")
MONGO_DATABASE_NAME = os.getenv("MONGO_DATABASE_NAME", "digital-signage")

async def check_db_connection():
    try:
        client = AsyncIOMotorClient(MONGO_DATABASE_URL)
        client = AsyncIOMotorClient(
            MONGO_DATABASE_URL, serverSelectionTimeoutMS=15000, socketTimeoutMS=15000
        )
        await client.admin.command("ping")
        logger.info("Database connection is successful")
    except Exception as err:
        logger.error(f"Database connection failed: {err}")


async def init_db():
    # global client
    try:
        if not MONGO_DATABASE_URL:
            raise ValueError("MONGO_DATABASE_URL environment variable is not set")
        if not MONGO_DATABASE_NAME:
            raise ValueError("MONGO_DATABASE_NAME environment variable is not set")
        client = AsyncIOMotorClient(MONGO_DATABASE_URL)
        client = AsyncIOMotorClient(
            MONGO_DATABASE_URL,
            maxPoolSize=50,  # Adjust as needed
            minPoolSize=10,  # Adjust as needed
            serverSelectionTimeoutMS=15000,
        )

        await init_beanie(
            database=client[MONGO_DATABASE_NAME],
            document_models=[Location, Floor, Building, VerticalConnector, Path, Event],
        )
        logger.info("MongoDB initialized successfully")
    except Exception as err:
        logger.error(f"Error initializing MongoDB: {err}")
        raise
