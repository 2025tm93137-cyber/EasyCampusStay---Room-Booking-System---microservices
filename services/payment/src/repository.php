<?php
declare(strict_types=1);
namespace CampusStay;

function payment_body(array $row): array {
    unset($row['created_at']);
    $row['amount_minor']=(int)$row['amount_minor'];
    return $row;
}

function payment_result(array $row): array {
    if ($row['status']==='DECLINED') return [402,(new BusinessError(402,'PAYMENT_DECLINED','The mock payment gateway declined the payment.',['payment_id'=>$row['id']]))->body()];
    return [201,payment_body($row)];
}

function charge(Database $db,array $payload): array {
    require_positive_amount($payload['amount_minor']);
    $db->lock('charge:'.$payload['booking_id']);
    $old=$db->one('SELECT * FROM payments WHERE booking_id=?',[$payload['booking_id']]);
    if ($old!==null) {
        if ((int)$old['amount_minor']!==$payload['amount_minor'] || $old['currency']!==$payload['currency'] || $old['simulation']!==$payload['simulation']) {
            throw new BusinessError(409,'PAYMENT_CONFLICT','The booking already has a different payment request.');
        }
        return payment_result($old);
    }
    if ($payload['simulation']==='slow_success') usleep((int)((float)setting('PAYMENT_DELAY_SECONDS','3')*1000000));
    $state=$payload['simulation']==='decline' ? 'DECLINED' : 'CHARGED';
    $id=uuid4();
    $db->execute('INSERT INTO payments(id,booking_id,amount_minor,currency,simulation,status) VALUES (?,?,?,?,?,?)',
                 [$id,$payload['booking_id'],$payload['amount_minor'],$payload['currency'],$payload['simulation'],$state]);
    return payment_result($db->one('SELECT * FROM payments WHERE id=?',[$id]));
}

function refund(Database $db,string $bid): array {
    $row=$db->one('SELECT * FROM payments WHERE booking_id=? FOR UPDATE',[$bid]);
    if ($row===null) throw new BusinessError(404,'PAYMENT_NOT_FOUND','There is no payment for this booking.');
    require_refundable($row['status']);
    if ($row['status']==='CHARGED') {
        $db->execute('INSERT INTO refunds(id,payment_id,amount_minor) VALUES (?,?,?)',[uuid4(),$row['id'],$row['amount_minor']]);
        $db->execute("UPDATE payments SET status='REFUNDED' WHERE id=?",[$row['id']]);
    }
    return payment_body($db->one('SELECT * FROM payments WHERE booking_id=?',[$bid]));
}
