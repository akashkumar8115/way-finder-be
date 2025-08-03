from fastapi import Request, HTTPException, status, Depends
# from src.core.permit.permit_service import PermitService
from src.services.permit.permit_service import PermitService
from src.core.authentication.cred_load import Actions, Resources, SECRET_KEY, ALGORITHM
from src.core.authentication.authentication import get_current_user, get_token_payload
from jose import jwt
from src.datamodel.database.userauth.AuthenticationTables import Entity, Address, User, Role, UserEntityRoleMap
from src.core.database.dbs.getdb import postresql as db
from sqlalchemy.sql import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

permit_service = PermitService()

async def verify_permissions(
    request: Request,
    resource: str,
    action: str,
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
        entity_key = token_payload.get("entity_key")
        user_uuid = token_payload.get("user_uuid")
        username = token_payload.get("username")

        

        
        # Check permission with Permit.io
        has_permission = await permit_service.check_permission(
            user_id=username,
            action=action,  # Use the parameter
            resource=resource,  # Use the parameter
            org_id=entity_key
        )

        if not has_permission:
            raise HTTPException(
                status_code=403, 
                detail=f"Not authorized to {action} {resource}"
            )
        
        # Add context to request state
        request.state.user_uuid = user_uuid
        request.state.entity_uuid = entity_uuid
        
        return has_permission  # Return something to satisfy the dependency

    except Exception as e:
        raise HTTPException(
                status_code=403, 
                detail=f"Not authorized to {action} {resource}"
            )
