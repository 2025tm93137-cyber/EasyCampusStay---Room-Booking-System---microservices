<?php
declare(strict_types=1);
namespace CampusStay;
require_once __DIR__.'/platform.php';
require_once __DIR__.'/rules.php';
require_once __DIR__.'/repository.php';

serve(function(string $method,string $path,string $cid): array {
    if ($path==='/api/v1/payments' && $method!=='POST') throw new BusinessError(405,'HTTP_ERROR','Method Not Allowed');
    if ($method==='POST' && $path==='/api/v1/payments') {
        $body=request_body();
        fields($body,['booking_id','amount_minor','currency','simulation'],['booking_id','amount_minor','currency']);
        $body['booking_id']=uuid_field($body['booking_id']);
        require_positive_amount($body['amount_minor']);
        if (!is_string($body['currency']) || !preg_match('/^[A-Z]{3}$/D',$body['currency'])) throw new BusinessError(422,'VALIDATION_ERROR','Currency must be three uppercase letters.');
        $body['simulation']=$body['simulation'] ?? 'success';
        if (!in_array($body['simulation'],['success','decline','slow_success'],true)) throw new BusinessError(422,'VALIDATION_ERROR','Unknown payment simulation.');
        return local_idempotent('payments:charge',require_key($_SERVER['HTTP_IDEMPOTENCY_KEY'] ?? null),$body,
                                fn(Database $db)=>charge($db,$body),$cid);
    }
    if (preg_match('#^/api/v1/payments/([^/]+)(/refund)?$#D',$path,$match)) {
        $bid=uuid_field($match[1]);
        if ($method==='POST' && isset($match[2])) {
            return local_idempotent('payments:refund',require_key($_SERVER['HTTP_IDEMPOTENCY_KEY'] ?? null),['booking_id'=>$bid],
                                   fn(Database $db)=>[200,refund($db,$bid)],$cid);
        }
        if ($method==='GET' && !isset($match[2])) {
            $db=new Database();
            try { $row=$db->one('SELECT * FROM payments WHERE booking_id=?',[$bid]); } finally { $db->close(); }
            if ($row===null) throw new BusinessError(404,'PAYMENT_NOT_FOUND','There is no payment for this booking.');
            return [200,payment_body($row)];
        }
    }
    throw new BusinessError(404,'HTTP_ERROR','Not Found');
});
