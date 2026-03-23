# -*- coding: utf-8 -*-
"""
Analytics API - 数据分析接口
提供销售统计、低库存预警、推荐等功能
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, select
from datetime import datetime, timedelta
from typing import Optional

from database import get_db
from models.product import Product, Category
from models.order import Order, OrderItem

router = APIRouter(prefix="/analytics", tags=["数据分析"])


def success_response(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


@router.get("/sales", operation_id="get_sales_stats")
async def get_sales_stats(
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    category_id: Optional[int] = Query(None, description="分类ID"),
    db: AsyncSession = Depends(get_db),
):
    """销售统计"""
    query = (
        select(
            Product.id,
            Product.name,
            Product.category_id,
            Category.name.label("category_name"),
            func.sum(OrderItem.quantity).label("total_sold"),
            func.sum(OrderItem.subtotal).label("total_revenue"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Category, Category.id == Product.category_id, isouter=True)
        .where(Order.status.in_(["paid", "shipped", "completed"]))
    )

    if start_date:
        query = query.where(Order.created_at >= start_date)
    if end_date:
        query = query.where(Order.created_at <= end_date)
    if category_id:
        query = query.where(Product.category_id == category_id)

    query = (
        query.group_by(Product.id, Product.name, Product.category_id, Category.name)
        .order_by(desc("total_revenue"))
        .limit(50)
    )
    
    result = await db.execute(query)
    results = result.all()

    stats = {
        "total_orders": 0,
        "total_revenue": 0.0,
        "total_items_sold": 0,
        "top_products": [],
    }

    order_count_query = select(func.count(Order.id))
    if start_date:
        order_count_query = order_count_query.where(Order.created_at >= start_date)
    if end_date:
        order_count_query = order_count_query.where(Order.created_at <= end_date)
    order_count_query = order_count_query.where(Order.status.in_(["paid", "shipped", "completed"]))
    
    order_count_result = await db.execute(order_count_query)
    stats["total_orders"] = order_count_result.scalar() or 0

    for r in results:
        stats["total_revenue"] += float(r.total_revenue or 0)
        stats["total_items_sold"] += int(r.total_sold or 0)
        stats["top_products"].append(
            {
                "product_id": r.id,
                "product_name": r.name,
                "category_id": r.category_id,
                "category_name": r.category_name,
                "total_sold": int(r.total_sold or 0),
                "total_revenue": float(r.total_revenue or 0),
            }
        )

    return success_response(stats)


@router.get("/low-stock", operation_id="get_low_stock_alert")
async def get_low_stock_alert(
    threshold: int = Query(10, description="库存预警阈值"),
    db: AsyncSession = Depends(get_db),
):
    """低库存预警"""
    query = (
        select(Product)
        .where(Product.stock > 0, Product.stock <= threshold, Product.status == 1)
        .order_by(Product.stock)
    )
    result = await db.execute(query)
    products = result.scalars().all()

    result_list = []
    for p in products:
        cat_result = await db.execute(select(Category.name).where(Category.id == p.category_id))
        category_name = cat_result.scalar()

        active_reserves_query = (
            select(func.sum(OrderItem.quantity))
            .join(Order, Order.id == OrderItem.order_id)
            .where(OrderItem.product_id == p.id, Order.status == "pending")
        )
        active_reserves_result = await db.execute(active_reserves_query)
        active_reserves = active_reserves_result.scalar() or 0

        result_list.append(
            {
                "product_id": p.id,
                "sku": p.sku,
                "name": p.name,
                "category_name": category_name,
                "current_stock": p.stock,
                "threshold": threshold,
                "pending_orders": int(active_reserves),
                "effective_stock": p.stock - int(active_reserves),
                "status": "warning" if p.stock <= 5 else "normal",
            }
        )

    return success_response({"count": len(result_list), "products": result_list})


@router.get("/recommend", operation_id="get_recommendations")
async def get_recommendations(
    category_id: Optional[int] = Query(None, description="指定分类"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db),
):
    """个性化推荐（基于销量和库存）"""
    query = (
        select(
            Product.id,
            Product.name,
            Product.price,
            Product.stock,
            Product.image_url,
            Category.name.label("category_name"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("sales_count"),
        )
        .outerjoin(OrderItem, OrderItem.product_id == Product.id)
        .outerjoin(Category, Category.id == Product.category_id)
        .where(Product.status == 1, Product.stock > 0)
    )

    if category_id:
        query = query.where(Product.category_id == category_id)

    query = (
        query.group_by(
            Product.id,
            Product.name,
            Product.price,
            Product.stock,
            Product.image_url,
            Category.name,
        )
        .order_by(desc("sales_count"), desc(Product.stock))
        .limit(limit)
    )
    
    result = await db.execute(query)
    products = result.all()

    recommendations = []
    for p in products:
        recommendations.append(
            {
                "product_id": p.id,
                "name": p.name,
                "price": float(p.price),
                "stock": p.stock,
                "image_url": p.image_url,
                "category_name": p.category_name,
                "sales_count": int(p.sales_count),
                "reason": "热销" if int(p.sales_count) > 10 else "库存充足",
            }
        )

    return success_response(recommendations)


@router.get("/category-stats", operation_id="get_category_stats")
async def get_category_stats(db: AsyncSession = Depends(get_db)):
    """各分类统计，包含商品数、销量、收入"""
    query = (
        select(
            Category.id,
            Category.name,
            func.count(Product.id).label("product_count"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("sales_count"),
            func.coalesce(func.sum(OrderItem.subtotal), 0).label("total_revenue"),
        )
        .outerjoin(Product, Product.category_id == Category.id)
        .outerjoin(OrderItem, OrderItem.product_id == Product.id)
        .outerjoin(Order, Order.id == OrderItem.order_id)
        .where(Order.status.in_(["paid", "shipped", "completed"]))
        .group_by(Category.id, Category.name)
    )
    
    result = await db.execute(query)
    categories = result.all()

    return success_response(
        [
            {
                "category_id": c.id,
                "category_name": c.name,
                "product_count": c.product_count or 0,
                "sales_count": int(c.sales_count or 0),
                "total_revenue": float(c.total_revenue or 0),
            }
            for c in categories
        ]
    )