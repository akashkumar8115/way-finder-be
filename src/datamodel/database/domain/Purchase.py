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

Base = declarative_base()

# ------------------ Coupons and Related Tables ------------------

class Coupons(Base):
    __tablename__ = "coupons"
    coupon_id = Column(Integer, primary_key=True, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    expiry_date = Column(DateTime, nullable=False)
    is_valid = Column(Boolean, default=True)
    description = Column(String(255))
    
    # Relationships
    commissions = relationship("Commission", back_populates="coupon", cascade="all, delete-orphan")
    purchases = relationship("Purchase", back_populates="coupon", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Coupons(coupon_id={self.coupon_id}, expiry_date={self.expiry_date})>"

class Commission(Base):
    __tablename__ = "commission"
    commission_id = Column(Integer, primary_key=True, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    commission_rate = Column(Integer, nullable=False)
    discount = Column(Integer)
    is_valid = Column(Boolean, default=True)
    description = Column(String(255))
    coupon_id = Column(Integer, ForeignKey("coupons.coupon_id"))
    
    # Relationships
    coupon = relationship("Coupons", back_populates="commissions")
    purchases = relationship("Purchase", back_populates="commission", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Commission(commission_id={self.commission_id}, commission_rate={self.commission_rate})>"

class Tax(Base):
    __tablename__ = "tax"
    tax_id = Column(Integer, primary_key=True, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    tax = Column(Float, nullable=False)
    
    # Relationships
    purchases = relationship("Purchase", back_populates="tax", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tax(tax_id={self.tax_id}, tax={self.tax})>"

class TaxTypes(Base):
    __tablename__ = "tax_types"
    tax_id = Column(Integer, primary_key=True, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    tax_type = Column(String(1000), nullable=False)
    tax_percentage = Column(Integer, nullable=False)
    
    def __repr__(self):
        return f"<TaxTypes(tax_id={self.tax_id}, tax_type={self.tax_type})>"

class Purchase(Base):
    __tablename__ = "purchase"
    purchase_id = Column(Integer, primary_key=True, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    purchase_rate = Column(Integer, nullable=False)
    description = Column(String(255))
    coupon_id = Column(Integer, ForeignKey("coupons.coupon_id"))
    commission_id = Column(Integer, ForeignKey("commission.commission_id"), nullable=False)
    tax_id = Column(Integer, ForeignKey("tax.tax_id"), nullable=False)
    
    # Relationships
    coupon = relationship("Coupons", back_populates="purchases")
    commission = relationship("Commission", back_populates="purchases")
    tax = relationship("Tax", back_populates="purchases")
    
    def __repr__(self):
        return f"<Purchase(purchase_id={self.purchase_id}, purchase_rate={self.purchase_rate})>"

class Comments(Base):
    __tablename__ = "comments"
    comment_id = Column(Integer, primary_key=True, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    comment = Column(String(10000), nullable=False)
    reaction = Column(String(10000))
    user_uuid = Column(String(100), ForeignKey("user.user_uuid"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="comments")
    
    def __repr__(self):
        return f"<Comments(comment_id={self.comment_id})>"