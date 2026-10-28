<?php

namespace App\Console;

use Illuminate\Console\Scheduling\Schedule;
use Illuminate\Foundation\Console\Kernel as ConsoleKernel;

class Kernel extends ConsoleKernel
{
    protected function schedule(Schedule $schedule)
    {
        $this->schedule = $schedule;
        $this->mileages();
        // $this->ghost();
        $this->lockScheduledPayout();
    }

    private function mileages()
    {
        if (config('zzt.cron.enabled.confirm_mileage') == true) {
            $this->schedule->command('zzt-cron:confim-mileage')
                ->timezone('Asia/Seoul')
                ->dailyAt('04:50');
        }
    }

    private function lockScheduledPayout()
    {
        $this->schedule->command('zzt-cron:lock-scheduled-payout')
            ->timezone('Asia/Seoul')->weeklyOn(2);
        // $this->schedule->command('zzt-cron:ghost')->hourly();
    }

    private function ghost()
    {
        $this->schedule->command('zzt-cron:ghost')->everyMinute();
    }
}
