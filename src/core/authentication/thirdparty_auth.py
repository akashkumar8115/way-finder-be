from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.requests import Request
import logging

from src.core.database.dbs.getdb import postresql as db
from src.core.authentication.authentication import login_flow
from src.core.authentication.cred_load import google_sso, facebook_sso, github_sso, linkedin_sso, microsoft_sso, spotify_sso, SESSION_COOKIE_NAME
from src.datamodel.datavalidation.user import Token

# initializing logging
logger = logging.getLogger(__name__)


thirdparty_route = APIRouter()


@thirdparty_route.get("/login/{app}", tags=["SSO Login", "Auth"])
async def login(app: str):
    if (app == 'google'):
        with google_sso:
            # return await google_sso.get_login_redirect(params={"prompt": "consent", "access_type": "offline"})
            return await google_sso.get_login_redirect()
    elif (app == 'facebook'):
        with facebook_sso:
            return await facebook_sso.get_login_redirect(params={"prompt": "consent", "access_type": "offline"})
    elif (app == 'github'):
        with github_sso:
            return await github_sso.get_login_redirect(params={"prompt": "consent", "access_type": "offline"})
    elif (app == 'linkedin'):
        with linkedin_sso:
            return await linkedin_sso.get_login_redirect(params={"prompt": "consent", "access_type": "offline"})
    elif (app == 'microsoft'):
        with microsoft_sso:
            return await microsoft_sso.get_login_redirect(params={"prompt": "consent", "access_type": "offline"})
    elif (app == 'spotify'):
        with spotify_sso:
            return await spotify_sso.get_login_redirect(params={"prompt": "consent", "access_type": "offline"})


@thirdparty_route.get("/v1/redirect", tags=['Google SSO'])
async def google_callback(request: Request, db: Session = Depends(db)) -> Token:
    """Process login response from Google and return user info"""
    try:
        with google_sso:
            user = await google_sso.verify_and_process(request)
        access_token = login_flow(user, db, 'thrid_party')
        
        redirect_url = f"/"
        response = JSONResponse({"redirect_url": redirect_url})
        response.set_cookie(key=SESSION_COOKIE_NAME, value=access_token, httponly=True, secure=True, samesite="lax", domain='localhost')
        # frontend_url = "http://localhost:3000"  # Change this to your frontend's base URL
        # access_token = login_flow(user=user_signup, db=db, auth_flow='sign_up')
        # redirect_url = f"{frontend_url}/"
        # response = JSONResponse({"redirect_url": redirect_url, SESSION_COOKIE_NAME: access_token})
        # response = RedirectResponse(url="http://localhost:3000/", status_code=status.HTTP_302_FOUND)
        # response = RedirectResponse(url="http://localhost:3000", status_code=status.HTTP_302_FOUND)
        # response.set_cookie(SESSION_COOKIE_NAME, access_token)
        return response
    except ValueError as e:
        logger.error(f'Following error occured {e}')
        raise HTTPException(status_code=400, detail=f"{e}")
    except Exception as e:
        logger.error(f'Following error occured {e}')
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred. Report this message to support: {e}")