from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer, Double, String, Date, DateTime, UUID, Boolean, JSON, URL, Numeric
from sqlalchemy_utils import URLType
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
# import datetime
from src.datamodel.database.Base import Base
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.types import Enum
import uuid


class User(Base):
    __tablename__ = 'user'
    user_uuid = Column(String(36), primary_key=True, nullable=False, index=True)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    first_name = Column(String(255), nullable=False)
    middle_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    inactive_date = Column(DateTime, nullable=True)
    phone_country_code = Column(String(10), nullable=True)
    phone_number = Column(String(15), nullable=True, unique=True)
    provider = Column(String(50), nullable=True)  # e.g., Account-01 or Okta
    sso_id = Column(String(100), nullable=True)      # SSO provider-specific identifier
    profile_pic = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)
    salt = Column(String(255), nullable=True)
    hash_algorithm = Column(String(255), nullable=True)
    address_id = Column(Integer, ForeignKey("address.address_id"), nullable=True)
    role_id = Column(Integer, ForeignKey("role.role_id") , nullable=False)

    # # Relationships
    # address = relationship("Address", back_populates="user", foreign_keys=[address_id])
    # login_audits = relationship("LoginAudit", back_populates="user", cascade="all, delete-orphan")
    # email_validations = relationship("EmailValidation", back_populates="user", cascade="all, delete-orphan")
    # password_reset = relationship("PasswordReset", back_populates="user", foreign_keys="[PasswordReset.user_uuid]") 
    # role_user_map = relationship("RoleUserMap", back_populates="user", foreign_keys="[RoleUserMap.user_uuid]", cascade="all, delete-orphan")
    # created_by_user = relationship("User", remote_side="User.user_uuid", foreign_keys=[created_by])    
    # updated_by_user = relationship("User", remote_side="User.user_uuid", foreign_keys=[updated_by])

    
    def __repr__(self):
        return f"<User(user_uuid={self.user_uuid}, username={self.username})>"


    
    # Rest of the class remains the same


    # # Relationships
    # address = relationship("Address", back_populates="user", foreign_keys=[address_id])
    # login_audits = relationship("LoginAudit", back_populates="user", cascade="all, delete-orphan")
    # email_validations = relationship("EmailValidation", back_populates="user", cascade="all, delete-orphan")
    # password_reset = relationship("PasswordReset", back_populates="user", foreign_keys="[PasswordReset.user_uuid]") 
    # role_user_map = relationship("RoleUserMap", back_populates="user", foreign_keys="[RoleUserMap.user_uuid]", cascade="all, delete-orphan")
    # created_by_user = relationship("User", remote_side="User.user_uuid", foreign_keys=[created_by])    
    # updated_by_user = relationship("User", remote_side="User.user_uuid", foreign_keys=[updated_by])

    
    def __repr__(self):
        return f"<User(user_uuid={self.user_uuid}, username={self.username})>"

class LoginAudit(Base):
    __tablename__ = 'login_audit'
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    login_id = Column(Integer, primary_key=True, nullable=False)
    wrong_login_attempt = Column(Integer)
    action = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=False)
    user_uuid = Column(String(36), ForeignKey('user.user_uuid'), nullable=False)
    
    # Relationships
    # user = relationship("User", back_populates="login_audits")
    
    def __repr__(self):
        return f"<LoginAudit(login_id={self.login_id}, action={self.action})>"

class EmailValidation(Base):
    __tablename__ = 'email_validation'
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    validation_id = Column(Integer, primary_key=True, nullable=False)
    status = Column(String(255), nullable=False)
    ip_address = Column(String(1000), nullable=False)
    user_uuid = Column(String(36), ForeignKey('user.user_uuid'), nullable=False)
    
    # Relationships
    # user = relationship("User", back_populates="email_validations")
    
    def __repr__(self):
        return f"<EmailValidation(validation_id={self.validation_id}, status={self.status})>"

class PasswordReset(Base):
    __tablename__ = 'password_reset'
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    reset_id = Column(Integer, primary_key=True, nullable=False)
    # reset_password_token = Column(String(255), nullable=False)
    # expiry_time = Column(DateTime, nullable=False)
    user_uuid = Column(String(36), ForeignKey('user.user_uuid'), nullable=False)
    old_password_hash = Column(String(255), nullable=True)
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    
    #  Relationships
    # user = relationship("User", back_populates="password_reset", foreign_keys=[user_uuid])
    # updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<PasswordReset(reset_id={self.reset_id}, expiry_time={self.expiry_time})>"
    
    
class Country(Base):
    __tablename__ = "country"
    country_id = Column(String, primary_key=True, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    country_name = Column(String(255), nullable=False)
    description = Column(String(255))
    created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    
    # Relationships
    # address = relationship("Address", back_populates="country", foreign_keys="[Address.country_id]", cascade="all, delete-orphan") 
    # created_by_user = relationship("User", foreign_keys=[created_by])
    # updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<Country(country_id={self.country_id}, country_name={self.country_name})>"

class State(Base):
    __tablename__ = "state"
    state_id = Column(String, primary_key=True, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    state_name = Column(String(255), nullable=True)
    description = Column(String(255))
    created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    
    #  Relationships
    # address = relationship("Address", back_populates="state", cascade="all, delete-orphan")
    # created_by_user = relationship("User", foreign_keys=[created_by])
    # updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<State(state_id={self.state_id}, state_name={self.state_name})>"

class City(Base):
    __tablename__ = "city"
    city_id = Column(String, primary_key=True, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    city_name = Column(String(255), nullable=False)
   
    description = Column(String(255))
    created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    
    #  Relationships
    # address = relationship("Address", back_populates="city", cascade="all, delete-orphan")
    # created_by_user = relationship("User", foreign_keys=[created_by])
    # updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<City(city_id={self.city_id}, city_name={self.city_name})>"

class Address(Base):
    __tablename__ = "address"

    address_id = Column(Integer, primary_key=True, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    street_address_1 = Column(String(255))
    street_address_2 = Column(String(255))
    state_name = Column(String(255), nullable=True)
    country_name = Column(String(255), nullable=False)
    zipcode = Column(String(20), nullable=False)
    is_valid = Column(Boolean, default=True, nullable=False)
    city_name = Column(String, ForeignKey("city.city_id"), nullable=False)
    state_id = Column(String, ForeignKey("state.state_id"), nullable=False)
    country_id = Column(String, ForeignKey("country.country_id"), nullable=False)
    created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK 
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK 
    
    # Relationships
    # country = relationship("Country", back_populates="address", foreign_keys=[country_id])
    # state = relationship("State", back_populates="address")
    # city = relationship("City", back_populates="address")
    # user = relationship("User", back_populates="address" , foreign_keys="[User.address_id]")
    # entity = relationship("Entity", back_populates="address")
    # created_by_user = relationship("User", foreign_keys=[created_by])
    # updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<Address(address_id={self.address_id}, city_name={self.city_name})>"
    
class  Entity(Base):
    __tablename__ = "entity"
    entity_uuid = Column(String(36), primary_key=True, nullable=False)
    entity_key = Column(String(36), nullable=True, unique=True)
    entity_type = Column(Enum("parent", "entity", "xpiteam", name="entity_type_enum"), nullable=False, index=True)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    name = Column(String(255), nullable=False)  # Common field for both parent and organization
    description = Column(String(255), nullable=True)  # Used for organizations
    headcount = Column(Integer, nullable=True)  # Used for parents
    domain = Column(String(255), nullable=True)  # Used for parents
    is_active = Column(Boolean, default=True, nullable=False)
    parent_uuid = Column(String(36), ForeignKey("entity.entity_uuid", ondelete="CASCADE"), nullable=True , default=None)  # Self-referential FK
    address_id = Column(Integer,nullable=True)
    created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    logo_url = Column(String(255), nullable=True)  # URL to the organization's logo
    # maxLimit = Column(
    #     MutableDict.as_mutable(JSON),
    #     nullable=False,
    #     default=lambda: {"screen": 0, "content": 0, "playlist": 0, "group": 0 , "organization": 0},
    # ) 
    # currentLimit= Column(
    #     MutableDict.as_mutable(JSON),
    #     nullable=False,
    #     default=lambda: {"screen": 0, "content": 0, "playlist": 0, "group": 0 , "organization": 0},
    # )    
    
    
    # Relationships
    # address = relationship("Address", back_populates="entity", cascade="all, delete-orphan")
    # parent = relationship("Entity", remote_side=[entity_uuid], back_populates="children")
    # children = relationship("Entity", back_populates="parent", cascade="all, delete-orphan")
    # role_entity_maps = relationship("RoleEntityMap", back_populates="entity", cascade="all, delete-orphan")
    # created_by_user = relationship("User", foreign_keys=[created_by])
    # updated_by_user = relationship("User", foreign_keys=[updated_by])

    def __repr__(self):
        return f"<Entity(entity_uuid={self.entity_uuid}, entity_type={self.entity_type}, name={self.name})>"


# ------------------ Role, RoleEntityMap, RoleUserMap, Permission, PermissionRoleMap ------------------

class Role(Base):
    __tablename__ = "role"
    role_id = Column(Integer, primary_key=True, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    role_name = Column(String(255), nullable=False)
    description = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    
    # Relationships
    # role_entity_map = relationship("RoleEntityMap", back_populates="role", cascade="all, delete-orphan")
    # role_user_map = relationship("RoleUserMap", back_populates="role", cascade="all, delete-orphan")
    # permission_role_map = relationship("PermissionRoleMap", back_populates="role", cascade="all, delete-orphan")
    # created_by_user = relationship("User", foreign_keys=[created_by])
    # updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<Role(role_id={self.role_id}, role_name={self.role_name})>"

# class RoleEntityMap(Base):
#     __tablename__ = "role_entity_map"

#     created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
#     updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
#     entity_uuid = Column(String(36), ForeignKey("entity.entity_uuid", ondelete="CASCADE"), primary_key=True, nullable=False)
#     role_id = Column(Integer, ForeignKey("role.role_id"), primary_key=True, nullable=False)
#     description = Column(String(255))
#     created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
#     updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK

#     # Relationships
#     # entity = relationship("Entity", back_populates="role_entity_maps")
#     # role = relationship("Role", back_populates="role_entity_map")
#     # created_by_user = relationship("User", foreign_keys=[created_by])
#     # updated_by_user = relationship("User", foreign_keys=[updated_by])

#     def __repr__(self):
#         return f"<RoleEntityMap(entity_uuid={self.entity_uuid}, role_id={self.role_id})>"

class UserEntityRoleMap(Base):
    __tablename__ = "user_enitity_role_map"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)    
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    user_uuid = Column(String, ForeignKey("user.user_uuid"), nullable=True)
    entity_uuid = Column(String, ForeignKey("entity.entity_uuid"), nullable=True)
    # entity_uuid = Column(String, nullable=True)
    role_id = Column(Integer, ForeignKey("role.role_id"), nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# class RoleUserMap(Base):
#     __tablename__ = "role_user_map"
#     updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
#     role_id = Column(Integer, ForeignKey("role.role_id"), primary_key=True, nullable=False)
#     user_uuid = Column(String(36), ForeignKey("user.user_uuid"), primary_key=True, nullable=False)
#     created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
#     updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    
#     # Relationships
#     # role = relationship("Role", back_populates="role_user_map")
#     # user = relationship("User", back_populates="role_user_map", foreign_keys=[user_uuid]) 
#     # created_by_user = relationship("User", foreign_keys=[created_by])
#     # updated_by_user = relationship("User", foreign_keys=[updated_by])
    
#     def __repr__(self):
#         return f"<RoleUserMap(role_id={self.role_id}, user_uuid={self.user_uuid})>"

class Permission(Base):
    __tablename__ = "permission"
    permission_id = Column(Integer, primary_key=True, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    permission_name = Column(String(1000), nullable=False)
    description = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    
    # Relationships
    # permission_role_map = relationship("PermissionRoleMap", back_populates="permission", cascade="all, delete-orphan")
    # created_by_user = relationship("User", foreign_keys=[created_by])
    # updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<Permission(permission_id={self.permission_id}, permission_name={self.permission_name})>"
    

class PermissionRoleMap(Base):
    __tablename__ = "permission_role_map"
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permission.permission_id"), primary_key=True, nullable=False)
    role_id = Column(Integer, ForeignKey("role.role_id"), primary_key=True, nullable=False)
    created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    
    #Relationships
    # permission = relationship("Permission", back_populates="permission_role_map")
    # role = relationship("Role", back_populates="permission_role_map")
    # created_by_user = relationship("User", foreign_keys=[created_by])
    # updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<PermissionRoleMap(permission_id={self.permission_id}, role_id={self.role_id})>"
    



class VerificationOTP(Base):
    """Table to store OTPs for email and phone verification"""
    __tablename__ = "verification_otps"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    identifier = Column(String, nullable=False, index=True)  # Email or phone number
    otp = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'email' or 'phone'
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    
    def is_expired(self):
        """Check if the OTP is expired"""
        return datetime.utcnow() > self.expires_at

class VerifiedIdentifier(Base):
    """Table to store verified emails and phone numbers"""
    __tablename__ = "verified_identifiers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    identifier = Column(String, nullable=False, unique=True, index=True)  # Email or phone number
    type = Column(String, nullable=False)  # 'email' or 'phone'
    verified_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String, nullable=True)  # Will be populated when user is created

    