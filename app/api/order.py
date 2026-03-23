# -*- coding: utf-8 -*-
"""
Order API - 订单管理接口
提供订单创建、查询、支付、取消等功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select, func
from sqlalchemy.orm import selectinload
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


@router.post("", operation_id="create_order")
async def create_order(request: OrderCreateRequest, db: AsyncSession = Depends(get_db)):
    """创建订单，支持多个商品同时下单"""
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

        product_result = await db.execute(select(Product).where(Product.id == product_id))
        product = product_result.scalar_one_or_none()
        if not product:
            return fail_response(404, f"商品ID {product_id} 不存在")
        if product.status != 1:
            return fail_response(400, f"商品 {product.name} 已下架")

        if reservation_id:
            res_result = await db.execute(
                select(InventoryReservation).where(InventoryReservation.reservation_id == reservation_id)
            )
            reservation = res_result.scalar_one_or_none()
            if not reservation:
                return fail_response(404, f"预留ID {reservation_id} 不存在")
            if reservation.status != "active":
                return fail_response(
                    400, f"预留 {reservation_id} 状态已为: {reservation.status}"
                )
            if reservation.expires_at < datetime.now():
                reservation.status = "expired"
                await db.commit()
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
        active_reserves_query = (
            select(InventoryReservation)
            .where(
                and_(
                    InventoryReservation.product_id == product_id,
                    InventoryReservation.status == "active",
                    InventoryReservation.expires_at > datetime.now(),
                )
            )
        )
        active_reserves_result = await db.execute(active_reserves_query)
        active_reserves = active_reserves_result.scalars().all()
        
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
    await db.flush()

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
        res_result = await db.execute(
            select(InventoryReservation).where(InventoryReservation.reservation_id == res_id)
        )
        reservation = res_result.scalar_one_or_none()
        if reservation:
            reservation.status = "confirmed"
            product_result = await db.execute(select(Product).where(Product.id == reservation.product_id))
            product = product_result.scalar_one_or_none()
            if product:
                product.stock -= reservation.quantity
                if product.stock == 0:
                    product.status = 2
            reservation.status = "confirmed"

    await db.commit()
    await db.refresh(order)

    # 返回时不包含 items，避免异步延迟加载问题
    return success_response(order.to_dict(include_items=False), "订单创建成功")


@router.get("", operation_id="list_orders")
async def list_orders(
    status: Optional[str] = Query(None, description="订单状态"),
    customer_phone: Optional[str] = Query(None, description="客户电话"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """订单列表"""
    query = select(Order)

    if status:
        query = query.where(Order.status == status)
    if customer_phone:
        query = query.where(Order.customer_phone == customer_phone)
    if start_date:
        query = query.where(Order.created_at >= start_date)
    if end_date:
        query = query.where(Order.created_at <= end_date)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    orders = result.scalars().all()

    return success_response(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "orders": [order.to_dict(include_items=False) for order in orders],
        }
    )


@router.get("/{order_no}", operation_id="get_order")
async def get_order(
    order_no: str = Path(..., description="订单编号，如 ORD2026032200001"),
    db: AsyncSession = Depends(get_db)
):
    """获取订单详情，包含订单基本信息和商品明细"""
    # 预加载 items 关系
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.order_no == order_no)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return success_response(order.to_dict(include_items=True))


@router.post("/{order_no}/pay", operation_id="pay_order")
async def pay_order(
    order_no: str = Path(..., description="要支付的订单编号"),
    payment_method: str = Query(..., description="支付方式: alipay(支付宝)/wechat(微信)/bank(银行卡)"),
    db: AsyncSession = Depends(get_db),
):
    """模拟支付订单，将订单状态从pending变为paid"""
    result = await db.execute(select(Order).where(Order.order_no == order_no))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if order.status != "pending":
        return fail_response(400, f"订单状态不允许支付，当前状态: {order.status}")

    order.status = "paid"
    order.payment_method = payment_method
    order.payment_time = datetime.now()
    await db.commit()

    return success_response(order.to_dict(include_items=False), "支付成功")


@router.post("/{order_no}/cancel", operation_id="cancel_order")
async def cancel_order(
    order_no: str = Path(..., description="要取消的订单编号"),
    reason: Optional[str] = Query(None, description="取消原因，可选"),
    db: AsyncSession = Depends(get_db),
):
    """取消订单，已支付订单会自动退款并恢复库存"""
    result = await db.execute(select(Order).where(Order.order_no == order_no))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if order.status in ["completed", "cancelled", "refunded"]:
        return fail_response(400, f"订单状态不允许取消，当前状态: {order.status}")

    order.status = "cancelled"
    if reason:
        order.remark = (order.remark or "") + f" [取消原因: {reason}]"

    if order.status == "paid":
        items_result = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
        items = items_result.scalars().all()
        for item in items:
            if item.reservation_id:
                res_result = await db.execute(
                    select(InventoryReservation).where(InventoryReservation.reservation_id == item.reservation_id)
                )
                reservation = res_result.scalar_one_or_none()
                if reservation:
                    reservation.status = "cancelled"
            product_result = await db.execute(select(Product).where(Product.id == item.product_id))
            product = product_result.scalar_one_or_none()
            if product:
                product.stock += item.quantity
                if product.status == 2:
                    product.status = 1

    await db.commit()

    return success_response(order.to_dict(include_items=False), "订单已取消")


@router.post("/{order_no}/refund")
async def refund_order(
    order_no: str,
    reason: Optional[str] = Query(None, description="退款原因"),
    db: AsyncSession = Depends(get_db),
):
    """模拟退款"""
    result = await db.execute(select(Order).where(Order.order_no == order_no))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if order.status not in ["paid", "shipped"]:
        return fail_response(400, f"订单状态不允许退款，当前状态: {order.status}")

    order.status = "refunded"
    if reason:
        order.remark = (order.remark or "") + f" [退款原因: {reason}]"

    items_result = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    items = items_result.scalars().all()
    for item in items:
        product_result = await db.execute(select(Product).where(Product.id == item.product_id))
        product = product_result.scalar_one_or_none()
        if product:
            product.stock += item.quantity
            if product.status == 2:
                product.status = 1

    await db.commit()

    return success_response(order.to_dict(include_items=False), "退款成功")


@router.patch("/{order_no}/status")
async def update_order_status(
    order_no: str,
    status: str = Query(..., description="状态: pending/paid/shipped/completed"),
    db: AsyncSession = Depends(get_db),
):
    """更新订单状态"""
    result = await db.execute(select(Order).where(Order.order_no == order_no))
    order = result.scalar_one_or_none()
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

    await db.commit()

    return success_response(order.to_dict(include_items=False), f"订单状态已更新为: {status}")