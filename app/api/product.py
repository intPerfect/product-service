# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select, func
from sqlalchemy.orm import joinedload
from typing import Optional
from database import get_db
from models.product import Product
from schemas.product import ProductCreate, ProductUpdate, ProductResponse, ListResponse

router = APIRouter(prefix="/products", tags=["商品管理"])


@router.get("", response_model=ListResponse, operation_id="list_products")
async def list_products(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    category_id: Optional[int] = Query(None, description="分类ID"),
    status: Optional[int] = Query(None, description="商品状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取商品列表（支持搜索和分页）"""
    query = select(Product).options(joinedload(Product.category))

    # 关键词搜索
    if keyword:
        query = query.where(
            or_(
                Product.name.like(f"%{keyword}%"),
                Product.sku.like(f"%{keyword}%"),
                Product.description.like(f"%{keyword}%"),
            )
        )

    # 分类筛选
    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    # 状态筛选
    if status is not None:
        query = query.where(Product.status == status)

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页
    offset = (page - 1) * page_size
    query = query.order_by(Product.id.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    products = result.scalars().all()

    return ListResponse(
        code=0, message="success", data=[p.to_dict() for p in products], total=total
    )


@router.get("/all", response_model=ListResponse, operation_id="get_all_products")
async def list_all_products(db: AsyncSession = Depends(get_db)):
    """获取所有商品（不分页，用于MCP工具调用）"""
    query = (
        select(Product)
        .options(joinedload(Product.category))
        .where(Product.status == 1)
        .order_by(Product.id)
    )
    result = await db.execute(query)
    products = result.scalars().all()
    return ListResponse(
        code=0,
        message="success",
        data=[p.to_dict() for p in products],
        total=len(products),
    )


@router.get(
    "/{product_id}", response_model=ProductResponse, operation_id="get_product_by_id"
)
async def get_product(
    product_id: int = Path(..., description="商品ID，唯一标识一个商品"),
    db: AsyncSession = Depends(get_db),
):
    """获取单个商品详情，包含商品名称、价格、库存、状态等完整信息"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.post("", response_model=ProductResponse)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    """创建商品"""
    # 检查SKU是否已存在
    result = await db.execute(select(Product).where(Product.sku == data.sku))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="SKU已存在")

    product = Product(**data.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int, data: ProductUpdate, db: AsyncSession = Depends(get_db)
):
    """更新商品"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 如果更新SKU，检查唯一性
    if "sku" in update_data and update_data["sku"] != product.sku:
        sku_result = await db.execute(
            select(Product).where(Product.sku == update_data["sku"])
        )
        existing = sku_result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="SKU已存在")

    for key, value in update_data.items():
        setattr(product, key, value)

    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", operation_id="delete_product")
async def delete_product(
    product_id: int = Path(..., description="要删除的商品ID"),
    db: AsyncSession = Depends(get_db),
):
    """删除指定商品，删除后不可恢复"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    await db.delete(product)
    await db.commit()
    return {"code": 0, "message": "删除成功"}


@router.patch("/{product_id}/stock", operation_id="update_product_stock")
async def update_stock(
    product_id: int = Path(..., description="商品ID"),
    stock: int = Query(..., ge=0, description="新的库存数量，必须>=0"),
    db: AsyncSession = Depends(get_db),
):
    """更新商品库存数量"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    product.stock = stock
    await db.commit()
    return {
        "code": 0,
        "message": "库存更新成功",
        "data": {"id": product.id, "stock": stock},
    }


@router.patch("/{product_id}/status", operation_id="update_product_status")
async def update_status(
    product_id: int = Path(..., description="商品ID"),
    status: int = Query(
        ..., ge=0, le=2, description="商品状态: 0-下架, 1-上架, 2-售罄"
    ),
    db: AsyncSession = Depends(get_db),
):
    """更新商品上下架状态"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    product.status = status
    await db.commit()
    return {
        "code": 0,
        "message": "状态更新成功",
        "data": {"id": product.id, "status": status},
    }
