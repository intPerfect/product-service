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
('电子产品', '手机、电脑、数码设备等电子产品', NULL, 1),
('服装服饰', '男装、女装、童装等服装类商品', NULL, 2),
('食品饮料', '茶叶、零食、饮品等食品类商品', NULL, 3);

-- 插入初始商品数据
INSERT INTO product (sku, name, description, price, cost, category_id, stock, status) VALUES
('ELEC-001', 'iPhone 15 Pro', '苹果最新旗舰手机，256GB存储，钛金属机身', 8999.00, 7500.00, 1, 100, 1),
('ELEC-002', 'MacBook Pro 14寸', 'M3 Pro芯片，16GB内存，性能强劲', 14999.00, 12500.00, 1, 50, 1),
('ELEC-003', 'AirPods Pro 第二代', '主动降噪真无线耳机，空间音频', 1899.00, 1400.00, 1, 200, 1),
('CLOTH-001', '男士休闲T恤', '100%纯棉面料，舒适透气，M码', 129.00, 45.00, 2, 500, 1),
('CLOTH-002', '女士夏季连衣裙', '新款夏季碎花设计，清新优雅', 299.00, 120.00, 2, 300, 1),
('TEA-001', '武夷山正山小种红茶', '福建武夷山原产地，传统松烟香，250g礼盒装', 89.00, 35.00, 3, 1000, 1),
('TEA-002', '云南滇红工夫茶', '云南大叶种红茶，蜜香浓郁，500g散装', 128.00, 55.00, 3, 800, 1),
('TEA-003', '安吉白茶', '浙江安吉特产，鲜爽甘甜，100g精品装', 198.00, 90.00, 3, 600, 1),
('TEA-004', '西湖龙井绿茶', '杭州西湖产区，明前特级，100g礼盒', 368.00, 180.00, 3, 400, 1),
('FOOD-001', '比利时手工巧克力', '比利时进口原料，手工制作，礼盒装200g', 199.00, 80.00, 3, 800, 1);
