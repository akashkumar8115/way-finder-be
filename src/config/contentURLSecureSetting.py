

# from functools import lru_cache
# from pydantic_settings import BaseSettings
# from src.core.authentication.cred_load import SECRET_KEY

# class Settings(BaseSettings):
#     SECRET_KEY: str = "771736ebcdabd0b90ea1b71bc8c18aa4f5bb33259b46e11d664d12a35e8e5359"
#     frontend_base_url: str="http://localhost:3000"
#     frontend_base_url_ed: str="http://localhost:8081"
#     origin_url: str="https://digital-signage-fe-wine.vercel.app,http://localhost:3000,https://ed79.vercel.app,https://digital-signage-fe-saas.vercel.app"
#     sqlalchemy_database_url: str="postgresql://neondb_owner:npg_wVEUOi4Ftg0Y@ep-wandering-glitter-a1ea8bys-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
#     session_cookie_name: str="digital-signage"
#     algorithm: str="HS256"
#     permit_api_key: str="permit_key_lQKhf2K0xTlAqE8xbZNFGKqtrhepSipH873IKX8O0YoIl25HFjRy9HeU4e6YhqkMbXnH8NJoPntFRKsafVNYSZ"
#     permit_pdp: str="https://cloudpdp.api.permit.io"
#     cloudinary_api_secret: str="1yCHMNWkKsuHSt9YIwF3UXZnpkg"

#     class Config:
#         env_file = ".env.local"
#         extra = "allow"

# @lru_cache()
# def get_settings():
#     return Settings()
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    SECRET_KEY: str="771736ebcdabd0b90ea1b71bc8c18aa4f5bb33259b46e11d664d12a35e8e5359"
    FRONTEND_BASE_URL: str="http://localhost:3000"
    FRONTEND_BASE_URL_ED: str="http://localhost:8081"
    ORIGIN_URL: str="https://digital-signage-fe-wine.vercel.app,http://localhost:3000,https://ed79.vercel.app,https://digital-signage-fe-saas.vercel.app"
    SQLALCHEMY_DATABASE_URL: str
    SESSION_COOKIE_NAME: str
    ALGORITHM: str
    PERMIT_API_KEY: str
    PERMIT_PDP: str
    CLOUDINARY_API_SECRET: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: Optional[int] = 120
    RESET_PASSWORD_EXPIRE_HOURS: Optional[int] = 120

    class Config:
        env_file = ".env.local"
        extra = "allow"

@lru_cache()
def get_settings():
    return Settings()
