<?php
class ModelSaleOrder extends Model {
	public function getTotal() {
		$query = $this->db->query("SELECT COUNT(*) AS total FROM `" . DB_PREFIX . "order`");
		return $query->row['total'];
	}
}
