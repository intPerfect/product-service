# -*- coding: utf-8 -*-
"""
Product Service - 商品服务
用于MCP网关测试的商品增删改查服务
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

from config import settings
from app.api import category, product, inventory, pricing, order, analytics, search

app = FastAPI(
    title="Product Service",
    description="商品服务 - 提供商品管理、库存管理、订单管理、价格计算等功能",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(category.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(pricing.router, prefix="/api")
app.include_router(order.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(product.router, prefix="/api")


@app.get("/")
async def root():
    return {"service": "Product Service", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import os
    import uvicorn

    reload = os.getenv("RELOAD", "true").lower() in ("true", "1", "yes")

    logger.info(
        f"启动商品服务: http://{settings.server_host}:{settings.server_port} (热更新: {reload})"
    )
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=reload,
        reload_dirs=["app"] if reload else None,
    )
