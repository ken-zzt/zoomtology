CREATE TABLE `zoom_order` (
  `order_id` int NOT NULL AUTO_INCREMENT,
  `product_id` int NOT NULL,
  `order_status_id` int NOT NULL DEFAULT '0' COMMENT '예약 상태',
  `note_status` tinyint DEFAULT NULL COMMENT '노트 상태 - 0: Open, 1: Closed',
  `status` varchar(20) NOT NULL DEFAULT 'pending' COMMENT 'pending, recording, canceled',
  `secret` varchar(64) DEFAULT 'sk_live_should_not_leak',
  PRIMARY KEY (`order_id`),
  KEY `product_id` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='주문';
CREATE TABLE `zoom_seller_charge` (
  `id` int NOT NULL AUTO_INCREMENT,
  `seller_id` int NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `zoom_seller_charge_ibfk_1` FOREIGN KEY (`seller_id`) REFERENCES `zoom_ms_seller` (`seller_id`) ON DELETE RESTRICT
) ENGINE=InnoDB;
