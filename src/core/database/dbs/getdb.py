# from src.core.database.dbs.sqlite.connect import get_db as sqlite
# from src.core.database.dbs.postgresql.connect import get_db as sqlite
from src.core.database.dbs.postgresql.connect import get_db as postresql
# from src.core.database.dbs.mongodb.connect import get_db as mongodb

# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.ext.declarative import declarative_base

# SQLALCHEMY_DATABASE_URL = "sqlite:///./digital_signage.db"

# engine = create_engine(
#     SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
# )
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = declarative_base()

# def sqlite():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
