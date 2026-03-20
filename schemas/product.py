# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ========== 分类Schema ==========
class CategoryBase(BaseModel):
    name: str = Field(..., description="分类名称")
    description: Optional[str] = Field(None, description="分类描述")
    parent_id: Optional[int] = Field(None, description="父分类ID")
    sort_order: int = Field(0, description="排序")
    status: int = Field(1, description="状态")


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    status: Optional[int] = None


class CategoryResponse(CategoryBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 商品Schema ==========
class ProductBase(BaseModel):
    sku: str = Field(..., description="商品SKU")
    name: str = Field(..., description="商品名称")
    description: Optional[str] = Field(None, description="商品描述")
    price: float = Field(..., description="商品价格")
    cost: Optional[float] = Field(0.00, description="成本价")
    category_id: Optional[int] = Field(None, description="分类ID")
    stock: int = Field(0, description="库存数量")
    status: int = Field(1, description="状态: 0-下架 1-上架 2-售罄")
    image_url: Optional[str] = Field(None, description="商品图片")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    category_id: Optional[int] = None
    stock: Optional[int] = None
    status: Optional[int] = None
    image_url: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    category_name: Optional[str] = None
    status_text: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 查询参数Schema ==========
class ProductQuery(BaseModel):
    keyword: Optional[str] = Field(None, description="搜索关键词")
    category_id: Optional[int] = Field(None, description="分类ID")
    status: Optional[int] = Field(None, description="商品状态")
    page: int = Field(1, description="页码")
    page_size: int = Field(20, description="每页数量")


# ========== 通用响应Schema ==========
class ApiResponse(BaseModel):
    code: int = Field(0, description="状态码")
    message: str = Field("success", description="消息")
    data: Optional[dict] = Field(None, description="数据")


class ListResponse(BaseModel):
    code: int = Field(0, description="状态码")
    message: str = Field("success", description="消息")
    data: List[dict] = Field(default_factory=list, description="数据列表")
    total: int = Field(0, description="总数")
