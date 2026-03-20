# -*- coding: utf-8 -*-
"""
Product Service - 商品服务
用于MCP网关测试的商品增删改查服务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import CORS_ORIGINS, HOST, PORT
from app.api import category, product

app = FastAPI(
    title="Product Service",
    description="商品服务 - MCP网关测试用",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(category.router, prefix="/api")
app.include_router(product.router, prefix="/api")


@app.get("/")
def root():
    return {
        "service": "Product Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    print(f"启动商品服务: http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, reload=False)
