# -*- coding: utf-8 -*-
"""
Search API - 商品搜索增强接口
提供比价、替代品推荐、热销榜等功能
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from typing import Optional, List

from database import get_db
from models.product import Product, Category

router = APIRouter(prefix="/products", tags=["商品搜索"])


def success_response(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


@router.post("/compare")
def compare_products(product_ids: List[int], db: Session = Depends(get_db)):
    """商品比价（批量查询）"""
    if not product_ids:
        return {"code": 400, "message": "商品ID列表不能为空"}

    if len(product_ids) > 10:
        return {"code": 400, "message": "最多支持10个商品对比"}

    products = db.query(Product).filter(Product.id.in_(product_ids)).all()

    if len(products) != len(product_ids):
        found_ids = {p.id for p in products}
        missing = set(product_ids) - found_ids
        return {"code": 404, "message": f"商品ID不存在: {missing}"}

    comparison = []
    for p in products:
        category_name = (
            db.query(Category.name).filter(Category.id == p.category_id).scalar()
        )
        comparison.append(
            {
                "product_id": p.id,
                "sku": p.sku,
                "name": p.name,
                "category_name": category_name,
                "price": float(p.price),
                "stock": p.stock,
                "stock_status": "充足"
                if p.stock > 20
                else ("紧张" if p.stock > 0 else "售罄"),
                "status": p.status,
                "image_url": p.image_url,
            }
        )

    comparison.sort(key=lambda x: x["price"])

    best_value = min(
        comparison, key=lambda x: x["price"] if x["stock"] > 0 else float("inf")
    )

    return success_response(
        {"products": comparison, "best_value": best_value, "count": len(comparison)}
    )


@router.get("/trending")
def get_trending_products(
    category_id: Optional[int] = Query(None, description="分类ID"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: Session = Depends(get_db),
):
    """热销商品榜单"""
    from models.order import OrderItem, Order

    query = (
        db.query(
            Product.id,
            Product.name,
            Product.price,
            Product.stock,
            Product.image_url,
            Category.name.label("category_name"),
            func.sum(OrderItem.quantity).label("sales_count"),
        )
        .outerjoin(OrderItem, OrderItem.product_id == Product.id)
        .outerjoin(Order, Order.id == OrderItem.order_id)
        .outerjoin(Category, Category.id == Product.category_id)
        .filter(Product.status == 1)
    )

    if category_id:
        query = query.filter(Product.category_id == category_id)

    products = (
        query.group_by(
            Product.id,
            Product.name,
            Product.price,
            Product.stock,
            Product.image_url,
            Category.name,
        )
        .order_by(desc("sales_count"))
        .limit(limit)
        .all()
    )

    trending = []
    for i, p in enumerate(products):
        rank = i + 1
        trending.append(
            {
                "rank": rank,
                "product_id": p.id,
                "name": p.name,
                "price": float(p.price),
                "stock": p.stock,
                "image_url": p.image_url,
                "category_name": p.category_name,
                "sales_count": int(p.sales_count or 0),
                "badge": "爆款" if rank <= 3 else ("热卖" if rank <= 5 else ""),
            }
        )

    return success_response(trending)


@router.get("/{product_id}/alternatives")
def get_alternatives(
    product_id: int,
    limit: int = Query(5, ge=1, le=20, description="返回数量"),
    db: Session = Depends(get_db),
):
    """替代商品推荐（同分类或相似价格）"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    alternatives = (
        db.query(Product)
        .filter(
            Product.id != product_id,
            Product.status == 1,
            Product.stock > 0,
            or_(
                Product.category_id == product.category_id,
                and_(
                    Product.price >= float(product.price) * 0.7,
                    Product.price <= float(product.price) * 1.3,
                ),
            ),
        )
        .order_by(desc(Product.stock))
        .limit(limit)
        .all()
    )

    result = []
    for alt in alternatives:
        category_name = (
            db.query(Category.name).filter(Category.id == alt.category_id).scalar()
        )
        price_diff = float(alt.price) - float(product.price)
        result.append(
            {
                "product_id": alt.id,
                "name": alt.name,
                "price": float(alt.price),
                "category_name": category_name,
                "stock": alt.stock,
                "price_diff": round(price_diff, 2),
                "price_diff_percent": round(
                    (price_diff / float(product.price)) * 100, 2
                )
                if float(product.price) > 0
                else 0,
                "reason": "同类商品"
                if alt.category_id == product.category_id
                else "价格相近",
            }
        )

    result.sort(key=lambda x: abs(x["price_diff"]))

    return success_response(
        {
            "original_product": {
                "id": product.id,
                "name": product.name,
                "price": float(product.price),
                "category_id": product.category_id,
            },
            "alternatives": result,
        }
    )


@router.get("/search/advanced")
def advanced_search(
    keyword: Optional[str] = Query(None, description="关键词"),
    category_id: Optional[int] = Query(None, description="分类ID"),
    min_price: Optional[float] = Query(None, description="最低价"),
    max_price: Optional[float] = Query(None, description="最高价"),
    in_stock_only: bool = Query(False, description="仅显示有货"),
    sort_by: str = Query(
        "relevance", description="排序: relevance/price_asc/price_desc/stock"
    ),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
):
    """高级搜索"""
    query = db.query(Product).filter(Product.status == 1)

    if keyword:
        query = query.filter(
            or_(
                Product.name.like(f"%{keyword}%"),
                Product.sku.like(f"%{keyword}%"),
                Product.description.like(f"%{keyword}%"),
            )
        )

    if category_id:
        query = query.filter(Product.category_id == category_id)

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    if in_stock_only:
        query = query.filter(Product.stock > 0)

    if sort_by == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort_by == "stock":
        query = query.order_by(Product.stock.desc())
    else:
        query = query.order_by(Product.id.desc())

    total = query.count()
    products = query.offset((page - 1) * page_size).limit(page_size).all()

    return success_response(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "products": [p.to_dict() for p in products],
        }
    )


from sqlalchemy import func
