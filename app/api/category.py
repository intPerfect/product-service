# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.product import Category
from schemas.product import CategoryCreate, CategoryUpdate, CategoryResponse, ListResponse

router = APIRouter(prefix="/categories", tags=["分类管理"])


@router.get("", response_model=ListResponse, operation_id="get_categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """获取所有分类列表"""
    query = select(Category).order_by(Category.sort_order, Category.id)
    result = await db.execute(query)
    categories = result.scalars().all()
    return ListResponse(
        code=0,
        message="success",
        data=[c.to_dict() for c in categories],
        total=len(categories)
    )


@router.get("/{category_id}", response_model=CategoryResponse, operation_id="get_category_by_id")
async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    """获取单个分类详情"""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    return category


@router.post("", response_model=CategoryResponse)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    """创建分类"""
    category = Category(**data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: int, data: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    """更新分类"""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)
    
    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/{category_id}")
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    """删除分类"""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    await db.delete(category)
    await db.commit()
    return {"code": 0, "message": "删除成功"}