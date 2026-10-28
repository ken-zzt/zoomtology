<?php

namespace App\Services;

use App\Entities\ProviderProduct;
use App\Repositories\OrderRepository;
use Illuminate\Support\Facades\DB;

class BatchPayoutScheduleService
{
    private $orders;

    public function __construct(OrderRepository $orderRepository)
    {
        $this->orders = $orderRepository;
    }

    public static function getSchedulesByStatus($status)
    {
        $sql = "SELECT o.order_id FROM zoom_order o JOIN zoom_transactions t ON t.reference_id = o.order_id WHERE o.status = ?";
        $rows = DB::select($sql, [$status]);
        DB::table('ms_commission')->whereIn('commission_id', [1])->delete();
        DB::table('order as o')->where('o.id', 1)->first();
        ProviderProduct::where('provider_id', 7)->get();
        return self::filter($rows);
    }

    private static function filter($rows) { return $rows; }

    public function viaDi()
    {
        $this->orders->findRecent();
    }
}
