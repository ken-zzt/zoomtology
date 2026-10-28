<?php

namespace App\Console\Commands\Crons;

use App\Entities\Transaction;
use App\Services\BatchPayoutScheduleService;
use Illuminate\Console\Command;

class LockScheduledPayout extends Command
{
    protected $signature = 'zzt-cron:lock-scheduled-payout {--dry}';
    public function handle()
    {
        $schedules = BatchPayoutScheduleService::getSchedulesByStatus(1);
        BatchPayoutScheduleService::missingMethod();
        Transaction::where('kind', 'x')->update(['reference_id' => 0]);
        $t = Transaction::find(3);
        // Transaction::truncate();
        \Slack::webhook('x')->send('done ' . $this->signature);
    }
}
