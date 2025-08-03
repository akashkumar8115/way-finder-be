from fastapi import Request, HTTPException, status, Depends
from src.core.authentication.authentication import get_token_payload
from jose import jwt
from src.core.database.dbs.getdb import postresql as db
from sqlalchemy.ext.asyncio import AsyncSession


def validate_token(
    request: Request,
):
    # Get token from request
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authentication token")
        
    try:
        token_type, token = auth_header.split()
        if token_type.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    try:
        # Validate token and get user
        token_payload = get_token_payload(token)

        entity_uuid = token_payload.get("entity_uuid")
        user_uuid = token_payload.get("user_uuid")
        role_id = token_payload.get("role_id")
        username = token_payload.get("username")
        first_name = token_payload.get("first_name")
        last_name = token_payload.get("last_name")
        entity_key = token_payload.get("entity_key")
        provider = token_payload.get("provider")
        
        if not entity_uuid:
            raise HTTPException(status_code=403, detail="entity_uuid not associated with any entity")

        if not user_uuid:
            raise HTTPException(status_code=403, detail="user_uuid not associated with any user")
        
        # Add context to request state
        request.state.user_uuid = user_uuid
        request.state.entity_uuid = entity_uuid
        request.state.role_id = role_id
        request.state.username = username
        request.state.first_name = first_name
        request.state.last_name = last_name
        request.state.entity_key = entity_key
        request.state.provider = provider
        
        
        return True

    except Exception as e:
        raise HTTPException(
                status_code=403, 
                detail=f"Token validation failed: {str(e)}"
            )
