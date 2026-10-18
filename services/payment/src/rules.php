<?php
declare(strict_types=1);
namespace CampusStay;

function require_positive_amount(mixed $amount): void {
    if (!is_int($amount) || $amount<=0) throw new BusinessError(422,'INVALID_AMOUNT','Amount must be a positive integer in currency minor units.');
}

function require_refundable(string $state): void {
    if (!in_array($state,['CHARGED','REFUNDED'],true)) throw new BusinessError(409,'PAYMENT_NOT_REFUNDABLE','Only a successful payment can be refunded.');
}
