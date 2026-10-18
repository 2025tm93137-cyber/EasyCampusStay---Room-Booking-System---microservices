<?php
declare(strict_types=1);
namespace CampusStay;
require_once __DIR__.'/platform.php';
require_once __DIR__.'/rules.php';
require_once __DIR__.'/repository.php';

serve(function(string $method,string $path,string $cid): array {
    if ($path==='/api/v1/notifications' && $method!=='POST') throw new BusinessError(405,'HTTP_ERROR','Method Not Allowed');
    if ($method==='POST' && $path==='/api/v1/notifications') {
        $body=request_body();
        fields($body,['booking_id','recipient','booking_state','simulation'],['booking_id','recipient','booking_state']);
        $body['booking_id']=uuid_field($body['booking_id']);
        $body['recipient']=text_field($body['recipient'],254);
        $body['booking_state']=text_field($body['booking_state'],24);
        $body['simulation']=$body['simulation'] ?? 'success';
        if (!in_array($body['simulation'],['success','fail_once'],true)) throw new BusinessError(422,'VALIDATION_ERROR','Unknown notification simulation.');
        return local_idempotent('notifications:send',require_key($_SERVER['HTTP_IDEMPOTENCY_KEY'] ?? null),$body,
                                fn(Database $db)=>[201,send_notification($db,$body)],$cid);
    }
    if (preg_match('#^/api/v1/notifications/([^/]+)(/retry)?$#D',$path,$match)) {
        $bid=uuid_field($match[1]);
        if ($method==='POST' && isset($match[2])) {
            return local_idempotent('notifications:retry',require_key($_SERVER['HTTP_IDEMPOTENCY_KEY'] ?? null),['booking_id'=>$bid],
                                   fn(Database $db)=>[200,retry_notification($db,$bid)],$cid);
        }
        if ($method==='GET' && !isset($match[2])) {
            $db=new Database();
            try { $row=$db->one('SELECT * FROM notifications WHERE booking_id=?',[$bid]); } finally { $db->close(); }
            if ($row===null) throw new BusinessError(404,'NOTIFICATION_NOT_FOUND','There is no notification for this booking.');
            return [200,notification_body($row)];
        }
    }
    throw new BusinessError(404,'HTTP_ERROR','Not Found');
});
