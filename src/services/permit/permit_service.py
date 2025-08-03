# from permit import Permit
from fastapi import HTTPException, status
from src.core.authentication.cred_load import PERMIT_PDP, PERMIT_API_KEY
from enum import Enum
from typing import List, Optional
import logging
from permit import (
    Permit,
    TenantRead,
    UserRead,
    RoleAssignmentRead,
    PermitApiError,
)

from src.datamodel.datavalidation.user import UserDetails
import uuid
import random
import re


def get_random_6_digit():
    return random.randint(100000, 999999)


# Logging configuration
logger = logging.getLogger(__name__)

class PermitService:
    def __init__(self):
        self.permit = Permit(
            pdp=PERMIT_PDP,
            token=PERMIT_API_KEY,
        )
        self.permit_client = self.permit.api



    # Create Role with Permission
    async def create_role(self, role_key: int, name: str, description: str = None):
    
        try:
            # Prepare the role data
            role_data = {
                "key": role_key,
                "name": name,
            }
            
            if description:
                role_data["description"] = description
                
            # Create the role in Permit.io
            role = await self.permit_client.roles.create(role_data)
            
            logger.info(f"Created role: {role_key} with name: {name}")
            return role
            
        except PermitApiError as e:
            logger.error(f"Error creating role in Permit.io: {e}", stack_info=True)
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message,
            )
        except Exception as e:
            logger.error(f"Unexpected error creating role: {e}", stack_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create role: {str(e)}"
            )



    async def create_org_only(self, name: str, description: str):
        try:
            # Create the tenant/organization
            random_number = get_random_6_digit()
            sanitized_name = re.sub(r'[^A-Za-z0-9\-_]', '_', name.lower())


            tenant: TenantRead = await self.permit_client.tenants.create({
                "key": f"{sanitized_name}-{random_number}",
                "name": name,
                "description": description
            })
            return tenant

        except PermitApiError as e:
            logger.error(msg=e, stack_info=True)
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message,
            )

    async def delete_org(self, tenant_key: str):
        """Delete an organization from Permit.io"""
        try:
            # Delete the tenant using the Permit.io client
            await self.permit_client.tenants.delete(tenant_key)
            return True
        except PermitApiError as e:
            logger.error(f"Error deleting organization from Permit.io: {e}")
            raise HTTPException(status_code=e.status_code, detail=e.message)
            
       

    async def create_org_in_permit(self, user: UserDetails):
        try:
            # Create the tenant/organization
            random_number = get_random_6_digit()

            sanitized_name = re.sub(r'[^A-Za-z0-9\-_]', '_', user.first_name.lower())

            tenant: TenantRead = await self.permit_client.tenants.create({
                "key": f"{sanitized_name}-org-{random_number}",
                "name": f"{user.first_name}'s Org"
            })

            # logger.info(f"Created tenant: {tenant}")

            # Then create the user
            new_user: UserRead = await self.permit_client.users.sync({
                "key": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                })
            
            # Finally assign role to user in the tenant
            await self.permit_client.users.assign_role(
                {"user": user.email, "role": user.role, "tenant": tenant.key}
            )

            return tenant

        except PermitApiError as e:
            logger.error(msg=e, stack_info=True)
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message,
            )
        
    async def get_digital_signage_org(self):
        """Fetch Digital-signage organization from Permit.io"""
        try:
            # Fetch existing Digital-signage tenant
            # tenant: TenantRead = await self.permit_client.tenants.get("digital-signage")
            tenant: TenantRead = await self.permit_client.tenants.get("xpilife-organization")
            return tenant
        except PermitApiError as e:
            logger.error(f"Error fetching Digital-signage org: {e}")
            raise HTTPException(status_code=e.status_code, detail=e.message)    

    async def update_org(self, tenant_key: str, name: str = None, description: str = None):
        
        try:
            # Prepare update data
            update_data = {}
            
            if name is not None:
                update_data["name"] = name
                
            if description is not None:
                update_data["description"] = description
                
            # Skip update if no changes requested
            if not update_data:
                # If no updates, just return the current tenant
                return await self.permit_client.tenants.get(tenant_key)
                
            # Update the tenant in Permit.io
            updated_tenant = await self.permit_client.tenants.update(tenant_key, update_data)
            
            logger.info(f"Updated organization: {tenant_key} with data: {update_data}")
            return updated_tenant
            
        except PermitApiError as e:
            logger.error(f"Error updating organization in Permit.io: {e}", stack_info=True)
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message,
            )
        except Exception as e:
            logger.error(f"Unexpected error updating organization: {e}", stack_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update organization: {str(e)}"
            )


    async def create_user_in_permit(self, user: UserDetails, org_key: str, role: str = "viewer"):
        try:
            # Then create the user
            new_user: UserRead = await self.permit_client.users.sync({
                "key": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                })
            
            # Finally assign role to user in the tenant
            await self.permit_client.users.assign_role(
                {"user": user.email, "role": role, "tenant": org_key}
            )

            return new_user

        except PermitApiError as e:
            logger.error(msg=e, stack_info=True)
            if e.status_code == 409:
                # Handle case where tenant/user already exists
                return await self.permit_client.users.get(user.email)
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message,
            )
        


    async def remove_user_from_permit(self, user_key: str, org_key: str, role: str = "viewer"):
        try:
            
            await self.permit_client.users.unassign_role(
                {"user": user_key, "role": role, "tenant": org_key}
            )

        except PermitApiError as e:
            logger.error(msg=e, stack_info=True)
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message,
            )    

    async def update_user_role(self, user_key: str, org_key: str, role: str = "viewer"):
        try:
            
            # Finally assign role to user in the tenant
            await self.permit_client.users.assign_role(
                {"user": user_key, "role": role, "tenant": org_key}
            )

        except PermitApiError as e:
            logger.error(msg=e, stack_info=True)
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message,
            )    
            



    async def update_user_organization(
        self, 
        old_org_key: str, 
        user=UserDetails,
        role: str = "admin"
    ):
        try:

            random_number = get_random_6_digit()
            sanitized_name = re.sub(r'[^A-Za-z0-9\-_]', '_', user.first_name.lower())
            
            # Create new organization in Permit.io
            new_tenant: TenantRead = await self.permit_client.tenants.create({
                "key": f"{sanitized_name}-org-{random_number}",
                "name": f"{user.first_name} Org"
            })

            # Remove from old organization
            await self.permit_client.users.unassign_role(
                {"user": user.email, "role": role, "tenant": old_org_key}
            )

             # Then create the user
            new_user: UserRead = await self.permit_client.users.sync({
                "key": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                })

            # # Finally assign role to user in the tenant
            await self.permit_client.users.assign_role(
                {"user": user.email, "role": role, "tenant": new_tenant.key}
            )

            return new_tenant
            
        # except PermitApiError as e:
        #     raise HTTPException(
        #         status_code=e.status_code,
        #         detail=e.message
        #     )    
        except PermitApiError as e:
            logger.error(msg=e, stack_info=True)
            if e.status_code == 409:
                # Handle case where tenant/user already exists
                return await self.permit_client.users.get(user.email)
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message,
            )

    async def update_user_role(
        self,
        user_id: str,
        org_key: str,
        role: str
    ):
    # """
    # Update user permissions based on plan type
    # Args:
    #     user_id (str): User's email/id
    #     org_key (str): Organization key
    #     plan_type (str): Subscription plan type (basic, premium, enterprise)
    # """
        try:
            
            await self.permit_client.users.assign_role({
                "user": user_id,
                "role": role,
                "tenant": org_key
            })

            logger.info(f"Updated permissions for user {user_id} to {role} in organization {org_key}")
            
            return {
                "user_id": user_id,
                "organization": org_key,
                "new_role": role,
                "status": "success"
            }

        except PermitApiError as e:
            logger.error(f"Permit.io API error while updating permissions: {e}")
            raise HTTPException(
                status_code=e.status_code,
                detail=f"Failed to update permissions: {e.message}"
            )
        except Exception as e:
            logger.error(f"Error updating user permissions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update permissions: {str(e)}"
            )    


    async def check_permission(self, user_id: str, action: str, resource: str, org_id: str):
        try:
            return await self.permit.check(
                {"key": user_id},
                action,
                {"type": resource, "tenant": org_id}
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Permission check failed: {str(e)}"
            )


async def create_role_with_assign_permission(self, role_key: str, name: str, description: str = None, permissions: List[dict] = None):
    """
    Create a new role in Permit.io
    
    Args:
        role_key (str): Unique identifier for the role
        name (str): Display name for the role
        description (str): Optional description of the role
        permissions (List[dict]): Optional list of permissions to assign to the role
                                  Each dict should have 'action' and 'resource' keys
    
    Returns:
        The created role object
    
    Raises:
        HTTPException: If role creation fails
    """
    try:
        # Prepare the role data
        role_data = {
            "key": role_key,
            "name": name,
        }
        
        if description:
            role_data["description"] = description
            
        # Create the role in Permit.io
        role = await self.permit_client.roles.create(role_data)
        
        # If permissions are provided, assign them to the role
        if permissions and isinstance(permissions, list):
            for permission in permissions:
                if 'action' in permission and 'resource' in permission:
                    await self.permit_client.roles.assign_permissions(
                        role_key, 
                        [{
                            "action": permission['action'],
                            "resource": permission['resource']
                        }]
                    )
        
        logger.info(f"Created role: {role_key} with name: {name}")
        return role
        
    except PermitApiError as e:
        logger.error(f"Error creating role in Permit.io: {e}", stack_info=True)
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except Exception as e:
        logger.error(f"Unexpected error creating role: {e}", stack_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create role: {str(e)}"
        )

