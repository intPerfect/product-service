# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.product import Category
from schemas.product import CategoryCreate, CategoryUpdate, CategoryResponse, ListResponse

router = APIRouter(prefix="/categories", tags=["分类管理"])


@router.get("", response_model=ListResponse)
def list_categories(db: Session = Depends(get_db)):
    """获取所有分类列表"""
    categories = db.query(Category).order_by(Category.sort_order, Category.id).all()
    return ListResponse(
        code=0,
        message="success",
        data=[c.to_dict() for c in categories],
        total=len(categories)
    )


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """获取单个分类详情"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    return category


@router.post("", response_model=CategoryResponse)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    """创建分类"""
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, data: CategoryUpdate, db: Session = Depends(get_db)):
    """更新分类"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)
    
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """删除分类"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    db.delete(category)
    db.commit()
    return {"code": 0, "message": "删除成功"}
