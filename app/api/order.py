# -*- coding: utf-8 -*-
"""
Order API - 订单管理接口
提供订单创建、查询、支付、取消等功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import uuid

from database import get_db
from models.product import Product
from models.order import Order, OrderItem, InventoryReservation, Coupon

router = APIRouter(prefix="/orders", tags=["订单管理"])


class OrderCreateRequest(BaseModel):
    items: list
    reservation_ids: Optional[list] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    shipping_address: Optional[str] = None
    remark: Optional[str] = None
    payment_method: Optional[str] = None


def success_response(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


def fail_response(code: int, message: str):
    return {"code": code, "message": message}


@router.post("")
def create_order(request: OrderCreateRequest, db: Session = Depends(get_db)):
    """创建订单"""
    if not request.items:
        return fail_response(400, "订单商品不能为空")

    order_no = f"ORD{uuid.uuid4().hex[:16].upper()}"
    total_amount = 0.0
    order_items = []
    confirmed_reservations = []

    for item in request.items:
        product_id = item.get("product_id")
        quantity = item.get("quantity", 1)
        reservation_id = item.get("reservation_id")

        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return fail_response(404, f"商品ID {product_id} 不存在")
        if product.status != 1:
            return fail_response(400, f"商品 {product.name} 已下架")

        if reservation_id:
            reservation = (
                db.query(InventoryReservation)
                .filter(InventoryReservation.reservation_id == reservation_id)
                .first()
            )
            if not reservation:
                return fail_response(404, f"预留ID {reservation_id} 不存在")
            if reservation.status != "active":
                return fail_response(
                    400, f"预留 {reservation_id} 状态已为: {reservation.status}"
                )
            if reservation.expires_at < datetime.now():
                reservation.status = "expired"
                db.commit()
                return fail_response(400, f"预留 {reservation_id} 已过期")
            if reservation.product_id != product_id:
                return fail_response(
                    400, f"预留 {reservation_id} 不属于商品 {product_id}"
                )
            if reservation.quantity < quantity:
                return fail_response(
                    400, f"预留数量不足，需要 {quantity}，实际 {reservation.quantity}"
                )
            confirmed_reservations.append(reservation_id)

        available_stock = product.stock
        active_reserves = (
            db.query(InventoryReservation)
            .filter(
                and_(
                    InventoryReservation.product_id == product_id,
                    InventoryReservation.status == "active",
                    InventoryReservation.expires_at > datetime.now(),
                )
            )
            .all()
        )
        for res in active_reserves:
            if res.reservation_id not in confirmed_reservations:
                available_stock -= res.quantity

        if available_stock < quantity:
            return fail_response(
                400, f"商品 {product.name} 库存不足，当前可用: {available_stock}"
            )

        subtotal = float(product.price) * quantity
        total_amount += subtotal

        order_items.append(
            {
                "product_id": product_id,
                "sku": product.sku,
                "product_name": product.name,
                "price": float(product.price),
                "quantity": quantity,
                "subtotal": subtotal,
                "reservation_id": reservation_id,
            }
        )

    order = Order(
        order_no=order_no,
        status="pending",
        total_amount=total_amount,
        discount_amount=0.0,
        customer_name=request.customer_name,
        customer_phone=request.customer_phone,
        shipping_address=request.shipping_address,
        remark=request.remark,
        payment_method=request.payment_method,
    )
    db.add(order)
    db.flush()

    for item in order_items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item["product_id"],
                sku=item["sku"],
                product_name=item["product_name"],
                price=item["price"],
                quantity=item["quantity"],
                subtotal=item["subtotal"],
                reservation_id=item.get("reservation_id"),
            )
        )

    for res_id in confirmed_reservations:
        reservation = (
            db.query(InventoryReservation)
            .filter(InventoryReservation.reservation_id == res_id)
            .first()
        )
        if reservation:
            reservation.status = "confirmed"
            product = (
                db.query(Product).filter(Product.id == reservation.product_id).first()
            )
            if product:
                product.stock -= reservation.quantity
                if product.stock == 0:
                    product.status = 2
            reservation.status = "confirmed"

    db.commit()
    db.refresh(order)

    return success_response(order.to_dict(), "订单创建成功")


@router.get("")
def list_orders(
    status: Optional[str] = Query(None, description="订单状态"),
    customer_phone: Optional[str] = Query(None, description="客户电话"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
):
    """订单列表"""
    query = db.query(Order)

    if status:
        query = query.filter(Order.status == status)
    if customer_phone:
        query = query.filter(Order.customer_phone == customer_phone)
    if start_date:
        query = query.filter(Order.created_at >= start_date)
    if end_date:
        query = query.filter(Order.created_at <= end_date)

    total = query.count()
    orders = (
        query.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return success_response(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "orders": [order.to_dict(include_items=False) for order in orders],
        }
    )


@router.get("/{order_no}")
def get_order(order_no: str, db: Session = Depends(get_db)):
    """获取订单详情"""
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return success_response(order.to_dict())


@router.post("/{order_no}/pay")
def pay_order(
    order_no: str,
    payment_method: str = Query(..., description="支付方式: alipay/wechat/bank"),
    db: Session = Depends(get_db),
):
    """模拟支付"""
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if order.status != "pending":
        return fail_response(400, f"订单状态不允许支付，当前状态: {order.status}")

    order.status = "paid"
    order.payment_method = payment_method
    order.payment_time = datetime.now()
    db.commit()

    return success_response(order.to_dict(), "支付成功")


@router.post("/{order_no}/cancel")
def cancel_order(
    order_no: str,
    reason: Optional[str] = Query(None, description="取消原因"),
    db: Session = Depends(get_db),
):
    """取消订单"""
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if order.status in ["completed", "cancelled", "refunded"]:
        return fail_response(400, f"订单状态不允许取消，当前状态: {order.status}")

    order.status = "cancelled"
    if reason:
        order.remark = (order.remark or "") + f" [取消原因: {reason}]"

    if order.status == "paid":
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        for item in items:
            if item.reservation_id:
                reservation = (
                    db.query(InventoryReservation)
                    .filter(InventoryReservation.reservation_id == item.reservation_id)
                    .first()
                )
                if reservation:
                    reservation.status = "cancelled"
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock += item.quantity
                if product.status == 2:
                    product.status = 1

    db.commit()

    return success_response(order.to_dict(), "订单已取消")


@router.post("/{order_no}/refund")
def refund_order(
    order_no: str,
    reason: Optional[str] = Query(None, description="退款原因"),
    db: Session = Depends(get_db),
):
    """模拟退款"""
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if order.status not in ["paid", "shipped"]:
        return fail_response(400, f"订单状态不允许退款，当前状态: {order.status}")

    order.status = "refunded"
    if reason:
        order.remark = (order.remark or "") + f" [退款原因: {reason}]"

    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.stock += item.quantity
            if product.status == 2:
                product.status = 1

    db.commit()

    return success_response(order.to_dict(), "退款成功")


@router.patch("/{order_no}/status")
def update_order_status(
    order_no: str,
    status: str = Query(..., description="状态: pending/paid/shipped/completed"),
    db: Session = Depends(get_db),
):
    """更新订单状态"""
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    valid_statuses = [
        "pending",
        "paid",
        "shipped",
        "completed",
        "cancelled",
        "refunded",
    ]
    if status not in valid_statuses:
        return fail_response(400, f"无效状态，有效值: {valid_statuses}")

    order.status = status
    if status == "paid" and not order.payment_time:
        order.payment_time = datetime.now()

    db.commit()

    return success_response(order.to_dict(), f"订单状态已更新为: {status}")
