# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from database import get_db
from models.product import Product
from schemas.product import ProductCreate, ProductUpdate, ProductResponse, ListResponse

router = APIRouter(prefix="/products", tags=["商品管理"])


@router.get("", response_model=ListResponse)
def list_products(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    category_id: Optional[int] = Query(None, description="分类ID"),
    status: Optional[int] = Query(None, description="商品状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取商品列表（支持搜索和分页）"""
    query = db.query(Product)
    
    # 关键词搜索
    if keyword:
        query = query.filter(
            or_(
                Product.name.like(f"%{keyword}%"),
                Product.sku.like(f"%{keyword}%"),
                Product.description.like(f"%{keyword}%")
            )
        )
    
    # 分类筛选
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    
    # 状态筛选
    if status is not None:
        query = query.filter(Product.status == status)
    
    # 获取总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    products = query.order_by(Product.id.desc()).offset(offset).limit(page_size).all()
    
    return ListResponse(
        code=0,
        message="success",
        data=[p.to_dict() for p in products],
        total=total
    )


@router.get("/all", response_model=ListResponse)
def list_all_products(db: Session = Depends(get_db)):
    """获取所有商品（不分页，用于MCP工具调用）"""
    products = db.query(Product).filter(Product.status == 1).order_by(Product.id).all()
    return ListResponse(
        code=0,
        message="success",
        data=[p.to_dict() for p in products],
        total=len(products)
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """获取单个商品详情"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.post("", response_model=ProductResponse)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    """创建商品"""
    # 检查SKU是否已存在
    existing = db.query(Product).filter(Product.sku == data.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU已存在")
    
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    """更新商品"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    
    # 如果更新SKU，检查唯一性
    if "sku" in update_data and update_data["sku"] != product.sku:
        existing = db.query(Product).filter(Product.sku == update_data["sku"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="SKU已存在")
    
    for key, value in update_data.items():
        setattr(product, key, value)
    
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """删除商品"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    db.delete(product)
    db.commit()
    return {"code": 0, "message": "删除成功"}


@router.patch("/{product_id}/stock")
def update_stock(product_id: int, stock: int = Query(..., ge=0), db: Session = Depends(get_db)):
    """更新库存"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    product.stock = stock
    db.commit()
    return {"code": 0, "message": "库存更新成功", "data": {"id": product.id, "stock": stock}}


@router.patch("/{product_id}/status")
def update_status(product_id: int, status: int = Query(..., ge=0, le=2), db: Session = Depends(get_db)):
    """更新商品状态"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    product.status = status
    db.commit()
    return {"code": 0, "message": "状态更新成功", "data": {"id": product.id, "status": status}}
