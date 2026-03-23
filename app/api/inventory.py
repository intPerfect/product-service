# -*- coding: utf-8 -*-
"""
Inventory API - 库存管理接口
提供库存预留、释放、检查等功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select
from datetime import datetime, timedelta
from typing import Optional
import uuid

from database import get_db
from models.product import Product
from models.order import InventoryReservation

router = APIRouter(prefix="/inventory", tags=["库存管理"])


def success_response(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


def fail_response(code: int, message: str):
    return {"code": code, "message": message}


@router.post("/reserve", operation_id="reserve_inventory")
async def reserve_inventory(
    product_id: int = Query(..., description="商品ID"),
    quantity: int = Query(..., ge=1, description="预留数量"),
    ttl_seconds: int = Query(300, ge=60, le=3600, description="预留有效期(秒)"),
    db: AsyncSession = Depends(get_db),
):
    """预留库存"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    if product.status != 1:
        raise HTTPException(status_code=400, detail="商品已下架")

    available_stock = product.stock
    reserve_query = (
        select(InventoryReservation)
        .where(
            and_(
                InventoryReservation.product_id == product_id,
                InventoryReservation.status == "active",
                InventoryReservation.expires_at > datetime.now(),
            )
        )
    )
    reserve_result = await db.execute(reserve_query)
    existing_reserves = reserve_result.scalars().all()
    
    for res in existing_reserves:
        available_stock -= res.quantity

    if available_stock < quantity:
        return fail_response(400, f"库存不足，当前可用: {available_stock}")

    reservation_id = f"res_{uuid.uuid4().hex[:16]}"
    expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

    reservation = InventoryReservation(
        reservation_id=reservation_id,
        product_id=product_id,
        quantity=quantity,
        status="active",
        expires_at=expires_at,
    )
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)

    return success_response(
        {
            "reservation_id": reservation_id,
            "product_id": product_id,
            "product_name": product.name,
            "quantity": quantity,
            "expires_at": reservation.expires_at.isoformat(),
            "available_after_reserve": available_stock - quantity,
        },
        "库存预留成功",
    )


@router.delete("/reserve/{reservation_id}", operation_id="release_reservation")
async def release_reservation(reservation_id: str, db: AsyncSession = Depends(get_db)):
    """释放库存预留"""
    result = await db.execute(
        select(InventoryReservation).where(InventoryReservation.reservation_id == reservation_id)
    )
    reservation = result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(status_code=404, detail="预留记录不存在")

    if reservation.status != "active":
        raise HTTPException(
            status_code=400, detail=f"预留状态已为: {reservation.status}"
        )

    reservation.status = "cancelled"
    await db.commit()

    return success_response(
        {"reservation_id": reservation_id, "status": "cancelled"}, "预留已释放"
    )


@router.post("/reserve/{reservation_id}/confirm", operation_id="confirm_reservation")
async def confirm_reservation(reservation_id: str, db: AsyncSession = Depends(get_db)):
    """确认预留（扣减实际库存）"""
    result = await db.execute(
        select(InventoryReservation).where(InventoryReservation.reservation_id == reservation_id)
    )
    reservation = result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(status_code=404, detail="预留记录不存在")

    if reservation.status != "active":
        raise HTTPException(
            status_code=400, detail=f"预留状态已为: {reservation.status}"
        )

    if reservation.expires_at < datetime.now():
        reservation.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="预留已过期")

    product_result = await db.execute(select(Product).where(Product.id == reservation.product_id))
    product = product_result.scalar_one_or_none()
    if not product or product.stock < reservation.quantity:
        raise HTTPException(status_code=400, detail="库存不足，无法确认")

    product.stock -= reservation.quantity
    if product.stock == 0:
        product.status = 2

    reservation.status = "confirmed"
    await db.commit()

    return success_response(
        {
            "reservation_id": reservation_id,
            "status": "confirmed",
            "product_id": reservation.product_id,
            "quantity_deducted": reservation.quantity,
            "remaining_stock": product.stock,
        },
        "预留已确认，库存已扣减",
    )


@router.get("/check/{product_id}", operation_id="check_inventory")
async def check_inventory(
    product_id: int = Path(..., description="商品ID，要查询库存的商品编号"),
    db: AsyncSession = Depends(get_db)
):
    """检查商品库存状态，返回总库存、预留数量、可用数量等信息"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    reserve_query = (
        select(InventoryReservation)
        .where(
            and_(
                InventoryReservation.product_id == product_id,
                InventoryReservation.status == "active",
                InventoryReservation.expires_at > datetime.now(),
            )
        )
    )
    reserve_result = await db.execute(reserve_query)
    active_reservations = reserve_result.scalars().all()

    reserved_quantity = sum(r.quantity for r in active_reservations)

    return success_response(
        {
            "product_id": product_id,
            "product_name": product.name,
            "total_stock": product.stock,
            "reserved_quantity": reserved_quantity,
            "available_quantity": product.stock - reserved_quantity,
            "product_status": product.status,
            "product_status_text": {0: "下架", 1: "上架", 2: "售罄"}.get(
                product.status, "未知"
            ),
            "active_reservations": [
                {
                    "reservation_id": r.reservation_id,
                    "quantity": r.quantity,
                    "expires_at": r.expires_at.isoformat(),
                }
                for r in active_reservations[:10]
            ],
            "total_reservation_count": len(active_reservations),
        }
    )


@router.post("/batch")
async def batch_inventory_operation(operations: list, db: AsyncSession = Depends(get_db)):
    """
    批量库存操作
    operations: [{"action": "reserve"|"release"|"confirm", "product_id": 1, "quantity": 1, "reservation_id": "xxx"}]
    """
    results = []
    for op in operations:
        action = op.get("action")
        product_id = op.get("product_id")

        try:
            if action == "reserve":
                quantity = op.get("quantity", 1)
                result = await reserve_inventory(product_id, quantity, 300, db)
                results.append(
                    {"action": action, "product_id": product_id, "result": result}
                )
            elif action == "release":
                reservation_id = op.get("reservation_id")
                result = await release_reservation(reservation_id, db)
                results.append(
                    {
                        "action": action,
                        "reservation_id": reservation_id,
                        "result": result,
                    }
                )
            elif action == "confirm":
                reservation_id = op.get("reservation_id")
                result = await confirm_reservation(reservation_id, db)
                results.append(
                    {
                        "action": action,
                        "reservation_id": reservation_id,
                        "result": result,
                    }
                )
            else:
                results.append({"action": action, "error": f"未知操作: {action}"})
        except Exception as e:
            results.append(
                {"action": action, "product_id": product_id, "error": str(e)}
            )

    return success_response(results)