<?php
declare(strict_types=1);
namespace CampusStay;

function require_confirmed(string $state): void {
    if ($state!=='CONFIRMED') throw new BusinessError(409,'BOOKING_NOT_CONFIRMED','A confirmation notification requires a confirmed booking.');
}
