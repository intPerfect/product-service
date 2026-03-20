# -*- coding: utf-8 -*-
-- 创建商品数据库
CREATE DATABASE IF NOT EXISTS product_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE product_db;

-- 创建商品分类表
CREATE TABLE IF NOT EXISTS category (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '分类名称',
    description VARCHAR(500) DEFAULT NULL COMMENT '分类描述',
    parent_id BIGINT DEFAULT NULL COMMENT '父分类ID',
    sort_order INT DEFAULT 0 COMMENT '排序',
    status TINYINT DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_parent_id (parent_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品分类表';

-- 创建商品表
CREATE TABLE IF NOT EXISTS product (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku VARCHAR(64) NOT NULL UNIQUE COMMENT '商品SKU',
    name VARCHAR(200) NOT NULL COMMENT '商品名称',
    description TEXT DEFAULT NULL COMMENT '商品描述',
    price DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '商品价格',
    cost DECIMAL(10, 2) DEFAULT 0.00 COMMENT '成本价',
    category_id BIGINT DEFAULT NULL COMMENT '分类ID',
    stock INT NOT NULL DEFAULT 0 COMMENT '库存数量',
    status TINYINT DEFAULT 1 COMMENT '状态: 0-下架 1-上架 2-售罄',
    image_url VARCHAR(500) DEFAULT NULL COMMENT '商品图片',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category_id (category_id),
    INDEX idx_status (status),
    INDEX idx_sku (sku),
    FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表';

-- 插入初始分类数据
INSERT INTO category (name, description, parent_id, sort_order) VALUES
('Electronics', 'Electronic devices', NULL, 1),
('Clothing', 'Clothing items', NULL, 2),
('Food', 'Food and beverages', NULL, 3);

-- 插入初始商品数据
INSERT INTO product (sku, name, description, price, cost, category_id, stock, status) VALUES
('ELEC-001', 'iPhone 15 Pro', 'Apple latest smartphone, 256GB', 8999.00, 7500.00, 1, 100, 1),
('ELEC-002', 'MacBook Pro 14', 'M3 Pro chip, 16GB RAM', 14999.00, 12500.00, 1, 50, 1),
('ELEC-003', 'AirPods Pro', 'Active noise cancellation wireless earbuds', 1899.00, 1400.00, 1, 200, 1),
('CLOTH-001', 'Men Casual T-Shirt', '100% cotton comfortable fabric, Size M', 129.00, 45.00, 2, 500, 1),
('CLOTH-002', 'Women Summer Dress', 'New summer style, floral design', 299.00, 120.00, 2, 300, 1),
('FOOD-001', 'Organic Black Tea', 'Wuyi Mountain Lapsang Souchong, 250g', 89.00, 35.00, 3, 1000, 1),
('FOOD-002', 'Handmade Chocolate', 'Belgium imported, gift box', 199.00, 80.00, 3, 800, 1);
