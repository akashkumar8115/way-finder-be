from dotenv import load_dotenv
from pathlib import Path
import os

from fastapi_sso.sso.google import GoogleSSO
from fastapi_sso.sso.facebook import FacebookSSO
from fastapi_sso.sso.linkedin import LinkedInSSO
from fastapi_sso.sso.microsoft import MicrosoftSSO
from fastapi_sso.sso.github import GithubSSO
from fastapi_sso.sso.spotify import SpotifySSO

# Define the path to the .env.local file
# directory_path = Path(__file__).parent
# env_file_path = directory_path.parent.parent.parent / '.env.local'
env_file_path = '.env.local'


# List of environment variable keys to clear
env_vars_to_clear = [
    "SECRET_KEY", "ALGORITHM", "SESSION_COOKIE_NAME", "ACCESS_TOKEN_EXPIRE_MINUTES",
    "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
    "FACEBOOK_CLIENT_ID", "FACEBOOK_CLIENT_SECRET",
    "LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET",
    "MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET",
    "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET",
    "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"
]

# Clear the environment variables
for var in env_vars_to_clear:
    if var in os.environ:
        del os.environ[var]

# Reload the environment variables from the .env.local file
load_dotenv(dotenv_path=env_file_path)

# Fetch environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
ALGORITHM = os.getenv("ALGORITHM")
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "default_session_cookie_name")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

PERMIT_API_KEY = os.getenv("PERMIT_API_KEY")
PERMIT_PDP = os.getenv("PERMIT_PDP")

RESET_PASSWORD_EXPIRE_MINUTES = os.getenv("RESET_PASSWORD_EXPIRE_MINUTES", 120)

# MinIO configuration - use environment variables in production
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "true").lower() == "true"

# Set the OAUTHLIB_INSECURE_TRANSPORT environment variable
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Initialize SSO clients
google_sso = GoogleSSO(
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET, 
    "http://localhost:3000/chat",
    allow_insecure_http=False
)

facebook_sso = FacebookSSO(
    FACEBOOK_CLIENT_ID,
    FACEBOOK_CLIENT_SECRET, 
    "http://localhost:8000/v1/redirect",
    allow_insecure_http=True
)

linkedin_sso = LinkedInSSO(
    LINKEDIN_CLIENT_ID,
    LINKEDIN_CLIENT_SECRET, 
    "http://localhost:8000/v1/redirect",
    allow_insecure_http=True
)

microsoft_sso = MicrosoftSSO(
    MICROSOFT_CLIENT_ID,
    MICROSOFT_CLIENT_SECRET, 
    "http://localhost:8000/v1/redirect",
    allow_insecure_http=True
)

github_sso = GithubSSO(
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET, 
    "http://localhost:8000/v1/redirect",
    allow_insecure_http=True
)

spotify_sso = SpotifySSO(
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET, 
    "http://localhost:8000/v1/redirect",
    allow_insecure_http=True
)




# Add these constants
class UserRoles:
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

class Actions:
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"

class Resources:
    CONTENT = "content"
    PLAYLIST = "playlist"
    SCREEN = "screen"
    ORGANIZATION = "organization"

