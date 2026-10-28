<?php

namespace App\Entities;

/**
 * The entity class associated with the 'zoom_transactions' table. SELECT nothing here.
 */
class Transaction extends ZZTBaseEntiry
{
	protected $table = 'transactions';
	protected $fillable = [
        'revenue',
        'nope_col',
	];

    public function scopeRecent($q) { return $q->where('a', 1); }
}
