import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from sqlalchemy import func
import time
from src.datamodel.datavalidation.user import UserDetails, UserUpdate,Token
from src.datamodel.database.userauth.AuthenticationTables import User , Role,UserEntityRoleMap, Entity
from src.services.permit.permit_service import PermitService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# initializing logging
logger = logging.getLogger(__name__)
permit_service = PermitService()

class DuplicateError(Exception):
    pass

async def add_user(db: AsyncSession, user: UserDetails) :
    if not user.provider and not user.password:
        raise ValueError("A password should be provided for non SSO registers")
    if not user.username:
        user.username = user.email     

    user_table = User(
        created_on = user.created_on,
        user_uuid = user.user_uuid,
        username=user.username,
        email = user.email,
        first_name = user.first_name,
        middle_name = user.middle_name,
        last_name = user.last_name,
        phone_country_code = user.phone_country_code,
        phone_number = user.phone_number,
        is_active = user.is_active,
        provider = user.provider,
        sso_id = user.sso_id,
        profile_pic = user.profile_pic,
        password_hash = user.password,
        role_id=user.role_id
    )

    db.add(user_table)
    await db.commit()

    # get entity key from the entity which is find by the entity_uuid
    query = select(Entity).where(Entity.entity_uuid == user.entity_uuid)
    result = await db.execute(query)
    entity = result.scalar_one_or_none()
    entity_key = entity.entity_key if entity else None

    # Find entity_uuid by entity_key for default entity
    query = select(Entity).where(Entity.entity_key == "xpilife-organization")
    result = await db.execute(query)
    entity = result.scalar_one_or_none()

    if entity:
        default_entity_uuid = entity.entity_uuid
    else:
        default_entity_uuid = None


    # add user to the permit.io

    await permit_service.create_user_in_permit(
        user= user_table,
        org_key= entity_key if entity_key else "xpilife-organization",
        role= user_table.role_id,
    )

         
    if user_table.role_id==2:
          user_org_role_map = UserEntityRoleMap(
            user_uuid = user_table.user_uuid,
            entity_uuid = user.entity_uuid,
            role_id = user_table.role_id,
         )
    if user_table.role_id==3:
          user_org_role_map = UserEntityRoleMap(
            user_uuid = user_table.user_uuid,
            entity_uuid = user.entity_uuid,
            role_id = user_table.role_id,
         )

    if user_table.role_id==1:
          user_org_role_map = UserEntityRoleMap(
            user_uuid = user.user_uuid,
            entity_uuid =user.entity_uuid,
            role_id = user.role_id,
         )  
    if user_table.role_id==4:
          user_org_role_map = UserEntityRoleMap(
            user_uuid = user.user_uuid,
            entity_uuid = default_entity_uuid,
            role_id = user.role_id,
         )          
    if user_table.role_id==5:
          user_org_role_map = UserEntityRoleMap(
            user_uuid = user.user_uuid,
            entity_uuid = user.entity_uuid,
            role_id = user.role_id,
         )      
          
    db.add(user_org_role_map)
    await db.commit()
    await db.refresh(user_org_role_map)

    try:
        db.add(user_table)
        await db.commit()
        await db.refresh(user_table)
    

    except IntegrityError as e:
        await db.rollback()
        logger.error(f'Following error occured while commiting to DB: {e}')
        raise DuplicateError(
            f"Username {user.username} is already attached to a registered user for the provider '{user.provider}'.")
    except Exception as e:
        logger.error(f'Following error occured while commiting to DB: {e}')
        raise HTTPException(status_code=403, detail=f"{e}")
    return user


# def get_user(db: Session, username: str, provider: str = 'local'):
#     user = db.query(User).filter(User.username == username).filter(User.provider == provider).first()
#     return user

async def get_user(db: AsyncSession, username: str, provider: str = 'local'):
    stmt = select(User).where(User.username == username, User.provider == provider)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    return user

# def get_password(db: Session, user_uuid: int):
#     password = db.query(Password).filter(Password.user_uuid == user_uuid).first()
#     return password.password_hash


def update_user(db: Session, user: UserUpdate):
    
    if not user.provider and not user.username:
        raise ValueError("A password should be provided for non SSO registers")
    user_details = get_user(db, user.username, user.provider)
    if not user_details:
        raise ValueError("User not found")
    

    provider = user.provider

    user_table = {
        "email" : user.email,
        "first_name" : user.first_name,
        "middle_name" : user.middle_name,
        "last_name" : user.last_name,
        "phone_country_code" : user.phone_country_code,
        "phone_number" : user.phone_number,
        "profile_pic" : user.profile_pic,
    }

    try:
        db.query(User).filter(User.username == user.username).filter(User.provider == provider).update(user_table)
        db.commit()
        if role_name:
            role = db.query(Role).filter_by(role_name=role_name).first()
            if not role:
                role = Role(role_name=role_name, created_on=datetime.utcnow())
                db.add(role)
                db.commit()
                db.refresh(role)

        existing_mapping = db.query(RoleUserMap).filter_by(user_uuid=user_details.user_uuid).first()
        if existing_mapping:
                existing_mapping.role_id = role.role_id
                existing_mapping.updated_on = datetime.utcnow()
        else:
                role_user_map = RoleUserMap(user_uuid=user_details.user_uuid, role_id=role.role_id, created_on=datetime.utcnow())
                db.add(role_user_map)
        db.commit() 
    except IntegrityError as e:
        db.rollback()
        logger.error(f'Following error occured while commiting to DB: {e}')
        raise DuplicateError(
            f"Username {user.username} is already attached to a registered user for the provider '{provider}'.")
    except Exception as e:
        logger.error(f'Following error occured while commiting to DB: {e}')
        raise HTTPException(status_code=403, detail=f"{e}")
    return user



# def all_members_data(db: Session, organization_id: str):
#     members_data = db.query(
#             User,
#             user_organizations.c.role
#         ).join(
#             user_organizations,
#             User.user_uuid == user_organizations.c.user_id
#         ).filter(
#             user_organizations.c.organization_id == organization_id
#         ).all()
    
#     return members_data




