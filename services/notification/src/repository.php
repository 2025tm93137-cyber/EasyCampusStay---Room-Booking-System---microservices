<?php
declare(strict_types=1);
namespace CampusStay;

function notification_body(array $row): array {
    unset($row['created_at']);
    $row['attempts']=(int)$row['attempts'];
    return $row;
}

function send_notification(Database $db,array $payload): array {
    require_confirmed($payload['booking_state']);
    $db->lock('notify:'.$payload['booking_id']);
    $old=$db->one('SELECT * FROM notifications WHERE booking_id=?',[$payload['booking_id']]);
    if ($old!==null) {
        if ($old['recipient']!==$payload['recipient']) throw new BusinessError(409,'NOTIFICATION_CONFLICT','The booking already has a different notification recipient.');
        return notification_body($old);
    }
    $id=uuid4();
    $state=$payload['simulation']==='fail_once' ? 'FAILED' : 'SENT';
    $db->execute('INSERT INTO notifications(id,booking_id,recipient,status,attempts,simulation) VALUES (?,?,?,?,1,?)',
                 [$id,$payload['booking_id'],$payload['recipient'],$state,$payload['simulation']]);
    return notification_body($db->one('SELECT * FROM notifications WHERE id=?',[$id]));
}

function retry_notification(Database $db,string $bid): array {
    $row=$db->one('SELECT * FROM notifications WHERE booking_id=? FOR UPDATE',[$bid]);
    if ($row===null) throw new BusinessError(404,'NOTIFICATION_NOT_FOUND','There is no notification for this booking.');
    if ($row['status']==='FAILED') $db->execute("UPDATE notifications SET status='SENT',attempts=attempts+1 WHERE booking_id=?",[$bid]);
    return notification_body($db->one('SELECT * FROM notifications WHERE booking_id=?',[$bid]));
}
