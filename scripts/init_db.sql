-- -*- coding: utf-8 -*-
-- Product Service Database Schema
-- 商品服务数据库表结构

CREATE DATABASE IF NOT EXISTS `product_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `product_db`;

-- 删除外键约束的表
DROP TABLE IF EXISTS `order_items`;
DROP TABLE IF EXISTS `orders`;
DROP TABLE IF EXISTS `inventory_reservation`;
DROP TABLE IF EXISTS `product`;
DROP TABLE IF EXISTS `category`;
DROP TABLE IF EXISTS `coupons`;
DROP TABLE IF EXISTS `member_levels`;

-- 商品分类表
CREATE TABLE `category` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL COMMENT '分类名称',
    `description` VARCHAR(500) DEFAULT NULL COMMENT '分类描述',
    `parent_id` BIGINT DEFAULT NULL COMMENT '父分类ID',
    `sort_order` INT DEFAULT 0 COMMENT '排序',
    `status` TINYINT DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_parent_id` (`parent_id`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品分类表';

-- 商品表
CREATE TABLE `product` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `sku` VARCHAR(64) NOT NULL UNIQUE COMMENT '商品SKU',
    `name` VARCHAR(200) NOT NULL COMMENT '商品名称',
    `description` TEXT DEFAULT NULL COMMENT '商品描述',
    `price` DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '商品价格',
    `cost` DECIMAL(10, 2) DEFAULT 0.00 COMMENT '成本价',
    `category_id` BIGINT DEFAULT NULL COMMENT '分类ID',
    `stock` INT NOT NULL DEFAULT 0 COMMENT '库存数量',
    `status` TINYINT DEFAULT 1 COMMENT '状态: 0-下架 1-上架 2-售罄',
    `image_url` VARCHAR(500) DEFAULT NULL COMMENT '商品图片',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_category_id` (`category_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_sku` (`sku`),
    FOREIGN KEY (`category_id`) REFERENCES `category`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表';

-- 会员等级表
CREATE TABLE `member_levels` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(32) UNIQUE NOT NULL COMMENT '等级名称',
    `discount_rate` DECIMAL(5, 2) NOT NULL DEFAULT 1.00 COMMENT '折扣率(0.95表示95折)',
    `points_multiplier` INT DEFAULT 1 COMMENT '积分倍数',
    `description` VARCHAR(200) DEFAULT NULL COMMENT '等级描述',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会员等级表';

-- 优惠券表
CREATE TABLE `coupons` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `code` VARCHAR(32) UNIQUE NOT NULL COMMENT '优惠券代码',
    `name` VARCHAR(100) NOT NULL COMMENT '优惠券名称',
    `discount_type` VARCHAR(20) NOT NULL COMMENT '折扣类型: fixed-立减, percent-百分比',
    `discount_value` DECIMAL(10, 2) NOT NULL COMMENT '折扣值',
    `min_purchase` DECIMAL(10, 2) DEFAULT 0.00 COMMENT '最低消费金额',
    `max_discount` DECIMAL(10, 2) DEFAULT NULL COMMENT '最大折扣金额',
    `valid_from` DATETIME DEFAULT NULL COMMENT '生效时间',
    `valid_until` DATETIME DEFAULT NULL COMMENT '失效时间',
    `usage_limit` INT DEFAULT 100 COMMENT '使用次数限制',
    `used_count` INT DEFAULT 0 COMMENT '已使用次数',
    `status` SMALLINT DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='优惠券表';

-- 库存预留表
CREATE TABLE `inventory_reservation` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `reservation_id` VARCHAR(64) UNIQUE NOT NULL COMMENT '预留ID',
    `product_id` BIGINT NOT NULL COMMENT '商品ID',
    `quantity` INT NOT NULL DEFAULT 1 COMMENT '预留数量',
    `status` VARCHAR(20) DEFAULT 'active' COMMENT '状态: active-有效, confirmed-已确认, cancelled-已取消, expired-已过期',
    `expires_at` DATETIME NOT NULL COMMENT '过期时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_product_id` (`product_id`),
    INDEX `idx_reservation_id` (`reservation_id`),
    INDEX `idx_status` (`status`),
    FOREIGN KEY (`product_id`) REFERENCES `product`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存预留表';

-- 订单表
CREATE TABLE `orders` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `order_no` VARCHAR(64) UNIQUE NOT NULL COMMENT '订单编号',
    `status` VARCHAR(20) DEFAULT 'pending' COMMENT '订单状态: pending-待支付, paid-已支付, shipped-已发货, completed-已完成, cancelled-已取消, refunded-已退款',
    `total_amount` DECIMAL(12, 2) NOT NULL DEFAULT 0.00 COMMENT '订单总额',
    `discount_amount` DECIMAL(12, 2) DEFAULT 0.00 COMMENT '折扣金额',
    `payment_method` VARCHAR(32) DEFAULT NULL COMMENT '支付方式',
    `payment_time` DATETIME DEFAULT NULL COMMENT '支付时间',
    `customer_name` VARCHAR(100) DEFAULT NULL COMMENT '客户姓名',
    `customer_phone` VARCHAR(20) DEFAULT NULL COMMENT '客户电话',
    `shipping_address` TEXT DEFAULT NULL COMMENT '收货地址',
    `remark` VARCHAR(500) DEFAULT NULL COMMENT '备注',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_order_no` (`order_no`),
    INDEX `idx_status` (`status`),
    INDEX `idx_customer_phone` (`customer_phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';

-- 订单明细表
CREATE TABLE `order_items` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `order_id` BIGINT NOT NULL COMMENT '订单ID',
    `product_id` BIGINT NOT NULL COMMENT '商品ID',
    `sku` VARCHAR(64) NOT NULL COMMENT '商品SKU',
    `product_name` VARCHAR(200) NOT NULL COMMENT '商品名称',
    `price` DECIMAL(10, 2) NOT NULL COMMENT '商品单价',
    `quantity` INT NOT NULL DEFAULT 1 COMMENT '购买数量',
    `subtotal` DECIMAL(12, 2) NOT NULL COMMENT '小计金额',
    `reservation_id` VARCHAR(64) DEFAULT NULL COMMENT '库存预留ID',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_order_id` (`order_id`),
    INDEX `idx_product_id` (`product_id`),
    FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`product_id`) REFERENCES `product`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单明细表';
