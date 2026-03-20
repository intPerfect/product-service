# -*- coding: utf-8 -*-
from sqlalchemy import Column, BigInteger, String, Text, DECIMAL, Integer, SmallInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Category(Base):
    """商品分类模型"""
    __tablename__ = "category"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    parent_id = Column(BigInteger, nullable=True)
    sort_order = Column(Integer, default=0)
    status = Column(SmallInteger, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parent_id": self.parent_id,
            "sort_order": self.sort_order,
            "status": self.status,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }


class Product(Base):
    """商品模型"""
    __tablename__ = "product"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sku = Column(String(64), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    cost = Column(DECIMAL(10, 2), default=0.00)
    category_id = Column(BigInteger, ForeignKey("category.id"), nullable=True)
    stock = Column(Integer, nullable=False, default=0)
    status = Column(SmallInteger, default=1)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    category = relationship("Category", foreign_keys=[category_id])

    def to_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "price": float(self.price) if self.price else 0.00,
            "cost": float(self.cost) if self.cost else 0.00,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "stock": self.stock,
            "status": self.status,
            "status_text": {0: "下架", 1: "上架", 2: "售罄"}.get(self.status, "未知"),
            "image_url": self.image_url,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }
