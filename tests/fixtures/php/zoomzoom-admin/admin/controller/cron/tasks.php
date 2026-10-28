<?php
class ControllerCronTasks extends Controller {
	public function index() {
	}
	public function statusCheck() {
		$this->load->zoomtu('order_info');
		$this->zzt_order_info->updateStatus(1, 2);
		$this->zzt_order_info->missingMethod();
		$this->model_sale_order->getTotal();
		$this->load->controller('common/header');
		$this->zzt_external_api->sendMessage([
			'key' => 'confirm-order',
			'payload' => ['orderId' => 1]
		], SEND_ORDER_QUEUE, 4);
		$f = function ($x) { return $x; };
	}
	protected function helper() {}
	public function _private_like() {}
}
