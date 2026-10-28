<?php
class ZZTCommissionBase extends Model {
	public function commissionInfoFromOrder($order_id) {
		$query = $this->db->query("SELECT * FROM " . DB_PREFIX . "order WHERE order_id = '" . (int)$order_id . "'");
		return $query->row;
	}
}
class ZZTCommission extends ZZTCommissionBase {
	public function calc() { return self::helper(); }
	private static function helper() { return 1; }
}
