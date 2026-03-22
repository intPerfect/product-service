# -*- coding: utf-8 -*-
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    DECIMAL,
    Integer,
    SmallInteger,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid


class InventoryReservation(Base):
    """库存预留模型"""

    __tablename__ = "inventory_reservation"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    reservation_id = Column(
        String(64),
        unique=True,
        nullable=False,
        default=lambda: f"res_{uuid.uuid4().hex[:16]}",
    )
    product_id = Column(BigInteger, ForeignKey("product.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    status = Column(String(20), default="active")
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    product = relationship("Product", foreign_keys=[product_id])

    def to_dict(self):
        return {
            "id": self.id,
            "reservation_id": self.reservation_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "quantity": self.quantity,
            "status": self.status,
            "expires_at": str(self.expires_at) if self.expires_at else None,
            "created_at": str(self.created_at) if self.created_at else None,
        }


class Order(Base):
    """订单模型"""

    __tablename__ = "orders"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_no = Column(
        String(64),
        unique=True,
        nullable=False,
        default=lambda: f"ORD{uuid.uuid4().hex[:16].upper()}",
    )
    status = Column(String(20), default="pending")
    total_amount = Column(DECIMAL(12, 2), nullable=False, default=0.00)
    discount_amount = Column(DECIMAL(12, 2), default=0.00)
    payment_method = Column(String(32), default=None)
    payment_time = Column(DateTime, default=None)
    customer_name = Column(String(100), default=None)
    customer_phone = Column(String(20), default=None)
    shipping_address = Column(Text, default=None)
    remark = Column(String(500), default=None)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )

    def to_dict(self, include_items=True):
        result = {
            "id": self.id,
            "order_no": self.order_no,
            "status": self.status,
            "status_text": {
                "pending": "待支付",
                "paid": "已支付",
                "shipped": "已发货",
                "completed": "已完成",
                "cancelled": "已取消",
                "refunded": "已退款",
            }.get(self.status, "未知"),
            "total_amount": float(self.total_amount) if self.total_amount else 0.00,
            "discount_amount": float(self.discount_amount)
            if self.discount_amount
            else 0.00,
            "payment_method": self.payment_method,
            "payment_time": str(self.payment_time) if self.payment_time else None,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "shipping_address": self.shipping_address,
            "remark": self.remark,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }
        if include_items:
            result["items"] = [item.to_dict() for item in self.items]
        return result


class OrderItem(Base):
    """订单明细模型"""

    __tablename__ = "order_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id = Column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id = Column(BigInteger, ForeignKey("product.id"), nullable=False)
    sku = Column(String(64), nullable=False)
    product_name = Column(String(200), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    subtotal = Column(DECIMAL(12, 2), nullable=False)
    reservation_id = Column(String(64), default=None)
    created_at = Column(DateTime, server_default=func.now())

    order = relationship("Order", back_populates="items")
    product = relationship("Product", foreign_keys=[product_id])

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "sku": self.sku,
            "product_name": self.product_name,
            "price": float(self.price) if self.price else 0.00,
            "quantity": self.quantity,
            "subtotal": float(self.subtotal) if self.subtotal else 0.00,
            "reservation_id": self.reservation_id,
            "created_at": str(self.created_at) if self.created_at else None,
        }


class Coupon(Base):
    """优惠券模型"""

    __tablename__ = "coupons"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    discount_type = Column(String(20), nullable=False)
    discount_value = Column(DECIMAL(10, 2), nullable=False)
    min_purchase = Column(DECIMAL(10, 2), default=0.00)
    max_discount = Column(DECIMAL(10, 2), default=None)
    valid_from = Column(DateTime, default=None)
    valid_until = Column(DateTime, default=None)
    usage_limit = Column(Integer, default=100)
    used_count = Column(Integer, default=0)
    status = Column(SmallInteger, default=1)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "discount_type": self.discount_type,
            "discount_value": float(self.discount_value)
            if self.discount_value
            else 0.00,
            "min_purchase": float(self.min_purchase) if self.min_purchase else 0.00,
            "max_discount": float(self.max_discount) if self.max_discount else None,
            "valid_from": str(self.valid_from) if self.valid_from else None,
            "valid_until": str(self.valid_until) if self.valid_until else None,
            "usage_limit": self.usage_limit,
            "used_count": self.used_count,
            "status": self.status,
            "created_at": str(self.created_at) if self.created_at else None,
        }


class MemberLevel(Base):
    """会员等级模型"""

    __tablename__ = "member_levels"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(32), unique=True, nullable=False)
    discount_rate = Column(DECIMAL(5, 2), nullable=False, default=1.00)
    points_multiplier = Column(Integer, default=1)
    description = Column(String(200), default=None)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "discount_rate": float(self.discount_rate) if self.discount_rate else 1.00,
            "points_multiplier": self.points_multiplier,
            "description": self.description,
        }
