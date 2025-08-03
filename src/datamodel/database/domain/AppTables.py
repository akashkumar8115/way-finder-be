from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Boolean,
    Float,
    ForeignKey,
    Numeric
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy_utils import URLType
from sqlalchemy.types import Enum

import src.datamodel.database.userauth.AuthenticationTables

Base = declarative_base()

# ------------------ Entity ------------------

class Entity(Base):
    __tablename__ = "entity"
    entity_uuid = Column(String(36), primary_key=True, nullable=False)
    entity_type = Column(Enum("parent", "organization", name="entity_type_enum"), nullable=False, index=True)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    name = Column(String(255), nullable=False)  # Common field for both parent and organization
    description = Column(String(255), nullable=True)  # Used for organizations
    headcount = Column(Integer, nullable=True)  # Used for parents
    domain = Column(String(255), nullable=True)  # Used for parents
    parent_uuid = Column(String(36), ForeignKey("entity.entity_uuid", ondelete="CASCADE"), nullable=True)  # Self-referential FK
    address_id = Column(Integer, nullable=True)
    created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    # Relationships
    address = relationship("Address", back_populates="entities", cascade="all, delete-orphan")
    parent = relationship("Entity", remote_side=[entity_uuid], back_populates="children")
    children = relationship("Entity", back_populates="parent", cascade="all, delete-orphan")
    role_entity_maps = relationship("RoleEntityMap", back_populates="entity", cascade="all, delete-orphan")
    created_by_user = relationship("User", foreign_keys=[created_by])
    updated_by_user = relationship("User", foreign_keys=[updated_by])

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
    created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    
    # Relationships
    role_entity_map = relationship("RoleEntityMap", back_populates="role", cascade="all, delete-orphan")
    role_user_map = relationship("RoleUserMap", back_populates="role", cascade="all, delete-orphan")
    permission_role_map = relationship("PermissionRoleMap", back_populates="role", cascade="all, delete-orphan")
    created_by_user = relationship("User", foreign_keys=[created_by])
    updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<Role(role_id={self.role_id}, role_name={self.role_name})>"

class RoleEntityMap(Base):
    __tablename__ = "role_entity_map"

    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    entity_uuid = Column(String(36), ForeignKey("entity.entity_uuid", ondelete="CASCADE"), primary_key=True, nullable=False)
    role_id = Column(Integer, ForeignKey("role.role_id"), primary_key=True, nullable=False)
    description = Column(String(255))
    created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK

    # Relationships
    entity = relationship("Entity", back_populates="role_entity_maps")
    role = relationship("Role", back_populates="role_entity_map")
    created_by_user = relationship("User", foreign_keys=[created_by])
    updated_by_user = relationship("User", foreign_keys=[updated_by])

    def __repr__(self):
        return f"<RoleEntityMap(entity_uuid={self.entity_uuid}, role_id={self.role_id})>"


class RoleUserMap(Base):
    __tablename__ = "role_user_map"
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("role.role_id"), primary_key=True, nullable=False)
    user_uuid = Column(String(36), ForeignKey("user.user_uuid"), primary_key=True, nullable=False)
    created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    
    # Relationships
    role = relationship("Role", back_populates="role_user_map")
    user = relationship("User", back_populates="role_user_map")
    created_by_user = relationship("User", foreign_keys=[created_by])
    updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<RoleUserMap(role_id={self.role_id}, user_uuid={self.user_uuid})>"

class Permission(Base):
    __tablename__ = "permission"
    permission_id = Column(Integer, primary_key=True, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    permission_name = Column(String(1000), nullable=False)
    description = Column(String(255))
    created_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    updated_by = Column(String(36), ForeignKey("user.user_uuid"), nullable=True)  # Self-referential FK
    
    # Relationships
    permission_role_map = relationship("PermissionRoleMap", back_populates="permission", cascade="all, delete-orphan")
    created_by_user = relationship("User", foreign_keys=[created_by])
    updated_by_user = relationship("User", foreign_keys=[updated_by])
    
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
    
    # Relationships
    permission = relationship("Permission", back_populates="permission_role_map")
    role = relationship("Role", back_populates="permission_role_map")
    created_by_user = relationship("User", foreign_keys=[created_by])
    updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<PermissionRoleMap(permission_id={self.permission_id}, role_id={self.role_id})>"