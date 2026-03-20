# -*- coding: utf-8 -*-
import os

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:123456@localhost:3306/product_db?charset=utf8mb4"
)

# 服务配置
HOST = "0.0.0.0"
PORT = 8778

# CORS配置
CORS_ORIGINS = ["*"]
