<?php
declare(strict_types=1);

function ui_settings(): array {
    $values=[];
    foreach (is_file(__DIR__.'/.env') ? file(__DIR__.'/.env',FILE_IGNORE_NEW_LINES) : [] as $line) {
        if (!str_contains($line,'=') || str_starts_with(trim($line),'#')) continue;
        [$key,$raw]=explode('=',$line,2);$raw=trim($raw);
        $values[trim($key)]=str_starts_with($raw,'"') ? json_decode($raw,true,512,JSON_THROW_ON_ERROR) : $raw;
    }
    foreach (['INVENTORY_URL','RESERVATION_URL','PAYMENT_URL','NOTIFICATION_URL','UI_ALLOWED_UPSTREAM_HOSTS'] as $key) {
        if (getenv($key)!==false) $values[$key]=getenv($key);
    }
    return $values;
}

function ui_session(): void {
    $folder=__DIR__.'/.runtime/sessions';
    if (!is_dir($folder)) mkdir($folder,0700,true);
    session_save_path($folder);
    session_name('campusstay_ui');
    session_set_cookie_params(['httponly'=>true,'samesite'=>'Strict','path'=>'/']);
    session_start();
    $_SESSION['csrf'] ??= bin2hex(random_bytes(24));
}

function upstream(string $service,string $method,string $path,?array $payload=null,?string $key=null): array {
    $values=ui_settings();
    $base=$values[strtoupper($service).'_URL'] ?? '';
    $parts=parse_url($base);
    $allowed=array_map('trim',explode(',', $values['UI_ALLOWED_UPSTREAM_HOSTS'] ?? '127.0.0.1,localhost'));
    if (!in_array($parts['host'] ?? '',$allowed,true) || ($parts['scheme'] ?? '')!=='http' || isset($parts['user']) || isset($parts['pass'])) {
        throw new RuntimeException('Configure the service URL and UI_ALLOWED_UPSTREAM_HOSTS.');
    }
    $cid='ui-'.bin2hex(random_bytes(8));
    $headers=['Content-Type: application/json','X-Correlation-ID: '.$cid];
    if ($key!==null) $headers[]='Idempotency-Key: '.$key;
    $curl=curl_init(rtrim($base,'/').$path);
    curl_setopt_array($curl,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_CUSTOMREQUEST=>$method,CURLOPT_HTTPHEADER=>$headers,
        CURLOPT_CONNECTTIMEOUT=>2,CURLOPT_TIMEOUT=>25,CURLOPT_FOLLOWLOCATION=>false,CURLOPT_PROXY=>'']);
    if ($payload!==null) curl_setopt($curl,CURLOPT_POSTFIELDS,json_encode($payload,JSON_THROW_ON_ERROR));
    $raw=curl_exec($curl);$status=(int)curl_getinfo($curl,CURLINFO_HTTP_CODE);
    if ($raw===false) { curl_close($curl); return ['status'=>503,'body'=>['error'=>['code'=>'SERVICE_UNAVAILABLE','message'=>ucfirst($service).' is not reachable. Check its container or service terminal and retry.','details'=>null]],'correlation_id'=>$cid]; }
    curl_close($curl);
    $body=json_decode($raw,true);
    if (!is_array($body)) return ['status'=>502,'body'=>['error'=>['code'=>'INVALID_UPSTREAM_RESPONSE','message'=>'A service returned an invalid response.','details'=>null]],'correlation_id'=>$cid];
    return ['status'=>$status,'body'=>$body,'correlation_id'=>$cid];
}
