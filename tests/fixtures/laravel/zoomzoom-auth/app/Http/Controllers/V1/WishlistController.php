<?php

namespace App\Http\Controllers\V1;

use App\Entities\Transaction;

class WishlistController extends ZZTBaseController
{
    public function add()
    {
        Transaction::create(['revenue' => 1]);
        return $this->ok();
    }

    private function ok() { return 1; }
}
