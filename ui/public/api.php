<?php
declare(strict_types=1);
require __DIR__.'/../bootstrap.php';
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
try {
    if ($_SERVER['REQUEST_METHOD']!=='POST') { http_response_code(405);echo json_encode(['error'=>'Use POST']);exit; }
    ui_session();
    $token=$_SERVER['HTTP_X_CSRF_TOKEN'] ?? '';
    $valid=hash_equals($_SESSION['csrf'],$token);
    session_write_close();
    if (!$valid) { http_response_code(403);echo json_encode(['error'=>'Refresh the page and retry.']);exit; }
    $raw=file_get_contents('php://input');
    if (strlen($raw)>65536) throw new RuntimeException('The request is too large.');
    $input=json_decode($raw,true,512,JSON_THROW_ON_ERROR);
    $action=$input['action'] ?? '';
    $payload=$input['payload'] ?? null;
    $key=$input['key'] ?? null;
    if ($key!==null && (!is_string($key) || preg_match('/[\r\n]/',$key))) throw new RuntimeException('Invalid request key.');
    if ($action==='health') {
        $items=[];
        foreach (['inventory','reservation','payment','notification'] as $name) $items[$name]=upstream($name,'GET','/health');
        $result=['status'=>200,'body'=>['services'=>$items]];
    } elseif ($action==='rooms') $result=upstream('inventory','GET','/api/v1/room-types');
    elseif ($action==='create_room') $result=upstream('inventory','POST','/api/v1/room-types',$payload,$key);
    elseif ($action==='book') $result=upstream('reservation','POST','/api/v1/bookings',$payload,$key);
    elseif (in_array($action,['booking','steps','payment','notification'],true)) {
        $bid=$input['booking_id'] ?? '';
        if (!is_string($bid) || !preg_match('/^[0-9a-f-]{36}$/iD',$bid)) throw new RuntimeException('Enter a valid booking ID.');
        $service=in_array($action,['booking','steps'],true) ? 'reservation' : $action;
        $path=match($action) {'booking'=>'/api/v1/bookings/','steps'=>'/api/v1/bookings/','payment'=>'/api/v1/payments/','notification'=>'/api/v1/notifications/'};
        $result=upstream($service,'GET',$path.rawurlencode($bid).($action==='steps'?'/steps':''));
    } elseif ($action==='availability') {
        $room=(string)($input['room_type_id'] ?? '');$day=(string)($input['stay_date'] ?? '');
        $result=upstream('inventory','GET','/api/v1/room-types/'.rawurlencode($room).'/availability?'.http_build_query(['stay_date'=>$day]));
    } else { http_response_code(422);echo json_encode(['error'=>'Unknown console action']);exit; }
    echo json_encode($result,JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR);
} catch (Throwable $error) {
    http_response_code(400);
    echo json_encode(['error'=>'Check the request, configuration and service terminals.']);
}
