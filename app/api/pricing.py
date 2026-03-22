# -*- coding: utf-8 -*-
"""
Pricing API - 价格计算接口
提供价格计算、优惠券校验等功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from database import get_db
from models.product import Product
from models.order import Coupon, MemberLevel, OrderItem

router = APIRouter(prefix="/pricing", tags=["价格计算"])


class PriceCalculateRequest(BaseModel):
    items: List[dict]
    member_level: Optional[str] = "normal"
    coupon_code: Optional[str] = None


def success_response(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


def fail_response(code: int, message: str):
    return {"code": code, "message": message}


@router.post("/calculate")
def calculate_price(request: PriceCalculateRequest, db: Session = Depends(get_db)):
    """
    计算最终价格
    items: [{"product_id": 1, "quantity": 2}, ...]
    """
    if not request.items:
        return fail_response(400, "商品列表不能为空")

    subtotal = 0.0
    item_details = []
    member_discount = 1.0

    if request.member_level and request.member_level != "normal":
        member = (
            db.query(MemberLevel)
            .filter(MemberLevel.name == request.member_level)
            .first()
        )
        if member:
            member_discount = float(member.discount_rate)

    for item in request.items:
        product_id = item.get("product_id")
        quantity = item.get("quantity", 1)

        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return fail_response(404, f"商品ID {product_id} 不存在")

        price = float(product.price)
        item_subtotal = price * quantity

        if member_discount < 1.0:
            item_subtotal = round(item_subtotal * member_discount, 2)

        subtotal += item_subtotal
        item_details.append(
            {
                "product_id": product_id,
                "product_name": product.name,
                "original_price": price,
                "quantity": quantity,
                "member_discount": member_discount,
                "subtotal": item_subtotal,
            }
        )

    discount_amount = 0.0
    coupon_info = None

    if request.coupon_code:
        coupon = (
            db.query(Coupon)
            .filter(and_(Coupon.code == request.coupon_code, Coupon.status == 1))
            .first()
        )

        if not coupon:
            return fail_response(404, "优惠券不存在或已禁用")

        now = datetime.now()
        if coupon.valid_from and now < coupon.valid_from:
            return fail_response(400, "优惠券尚未生效")
        if coupon.valid_until and now > coupon.valid_until:
            return fail_response(400, "优惠券已过期")
        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            return fail_response(400, "优惠券已用完")

        if subtotal < float(coupon.min_purchase):
            return fail_response(
                400, f"订单金额需满 {coupon.min_purchase} 元方可使用此券"
            )

        if coupon.discount_type == "fixed":
            discount_amount = float(coupon.discount_value)
        elif coupon.discount_type == "percent":
            discount_amount = round(subtotal * float(coupon.discount_value) / 100, 2)

        if coupon.max_discount and discount_amount > float(coupon.max_discount):
            discount_amount = float(coupon.max_discount)

        coupon_info = {
            "code": coupon.code,
            "name": coupon.name,
            "discount_type": coupon.discount_type,
            "discount_value": float(coupon.discount_value),
            "original_discount": discount_amount,
        }

    final_amount = round(subtotal - discount_amount, 2)
    if final_amount < 0:
        final_amount = 0.01

    return success_response(
        {
            "items": item_details,
            "subtotal": round(subtotal, 2),
            "member_discount": member_discount,
            "coupon": coupon_info,
            "discount_amount": round(discount_amount, 2),
            "final_amount": final_amount,
            "savings": round(subtotal - final_amount, 2),
        }
    )


@router.get("/coupons/{code}")
def get_coupon_info(code: str, db: Session = Depends(get_db)):
    """获取优惠券信息"""
    coupon = db.query(Coupon).filter(Coupon.code == code).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")

    now = datetime.now()
    is_valid = True
    invalid_reason = None

    if coupon.status != 1:
        is_valid = False
        invalid_reason = "优惠券已禁用"
    elif coupon.valid_from and now < coupon.valid_from:
        is_valid = False
        invalid_reason = "优惠券尚未生效"
    elif coupon.valid_until and now > coupon.valid_until:
        is_valid = False
        invalid_reason = "优惠券已过期"
    elif coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
        is_valid = False
        invalid_reason = "优惠券已用完"

    data = coupon.to_dict()
    data["is_valid"] = is_valid
    data["invalid_reason"] = invalid_reason

    return success_response(data)


@router.post("/coupons/apply")
def apply_coupon(
    code: str,
    order_amount: float = Query(..., description="订单金额"),
    db: Session = Depends(get_db),
):
    """试算优惠券"""
    coupon = db.query(Coupon).filter(Coupon.code == code).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")

    now = datetime.now()
    if coupon.status != 1:
        return fail_response(400, "优惠券已禁用")
    if coupon.valid_from and now < coupon.valid_from:
        return fail_response(400, "优惠券尚未生效")
    if coupon.valid_until and now > coupon.valid_until:
        return fail_response(400, "优惠券已过期")
    if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
        return fail_response(400, "优惠券已用完")
    if order_amount < float(coupon.min_purchase):
        return fail_response(400, f"订单金额需满 {coupon.min_purchase} 元")

    discount = 0.0
    if coupon.discount_type == "fixed":
        discount = min(float(coupon.discount_value), order_amount)
    elif coupon.discount_type == "percent":
        discount = round(order_amount * float(coupon.discount_value) / 100, 2)
        if coupon.max_discount:
            discount = min(discount, float(coupon.max_discount))

    return success_response(
        {
            "code": coupon.code,
            "name": coupon.name,
            "discount_type": coupon.discount_type,
            "discount_value": float(coupon.discount_value),
            "order_amount": order_amount,
            "discount_amount": discount,
            "final_amount": round(order_amount - discount, 2),
        }
    )


@router.get("/member-levels")
def list_member_levels(db: Session = Depends(get_db)):
    """获取会员等级列表"""
    levels = db.query(MemberLevel).filter().all()
    return success_response([level.to_dict() for level in levels])
