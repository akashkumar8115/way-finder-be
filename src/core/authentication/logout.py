from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from src.core.authentication.cred_load import SESSION_COOKIE_NAME

logout_route = APIRouter()


@logout_route.post("/logout", summary="Logout a user", tags=["Auth"])
def logout():
    try:
        response = JSONResponse(content={"message": "Logged out successfully"}, status_code=200)
        response.delete_cookie(
            key=SESSION_COOKIE_NAME,
            # value=None,
            path="/login",
            httponly=True,
            secure=True,
            samesite="none",
            domain=None,
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during logout: {e}"
        )
