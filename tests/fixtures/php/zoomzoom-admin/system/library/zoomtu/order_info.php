<?php
/**
 * ZZTOrderInfo — 테스트 fixture. "SELECT" 같은 낱말이 주석에 있어도 산출물엔 들어가지 않는다.
 */
class ZZTOrderInfo extends Model
{
	static $order_status_string = [
		"1" => "book_requested",
		"2" => "book_confirmed"
	];
	private static $secretMap = ['token' => 'abcdef123456'];

	function updateStatus($order_id, $status) {
		$sql = "UPDATE " . DB_PREFIX . "order SET order_status_id = ". $status .", date_modified = NOW() " .
			"WHERE order_id=" . $order_id ." AND order_status_id = 0";
		$this->db->query($sql);
		return $this->db->countAffected();
	}

	public function getOrder ( $order_id )
	{
		$sql = "SELECT o.*, op.name FROM `" . DB_PREFIX . "order` o " .
			"LEFT JOIN " . DB_PREFIX . "order_product op ON o.order_id = op.order_id ";
		if ($order_id) {
			$sql .= " WHERE o.order_id = " . (int)$order_id;
		}
		$res = $this->read_db->query($sql);
		$this->zzt_commission->commissionInfoFromOrder($order_id);
		$this->log($res);
		$this->nope($res);
		return $res->rows;
	}

	public function copyRequest($id) {
		$this->db->query("INSERT INTO " . DB_PREFIX . "ms_requestpayment (order_id) SELECT order_id FROM " . DB_PREFIX . "order WHERE order_id = " . (int)$id);
		$this->db->query("DELETE FROM " . DB_PREFIX . "ghost_table WHERE id = 1");
		$this->stats_db->query("SELECT * FROM zoom_stats_data WHERE d = '" . $this->db->escape($id) . "'");
		$this->db->query("SELECT 1 FROM " . $this->dynamic_table . " WHERE 1");
	}

	private function log($x) { return $x; }
}
