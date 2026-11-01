<?php
declare(strict_types=1);
// Exercise the UI without any local .env, matching an environment-only image.
$folder=sys_get_temp_dir().'/easystay-ui-'.bin2hex(random_bytes(6));
mkdir($folder,0700);
copy(__DIR__.'/../ui/bootstrap.php',$folder.'/bootstrap.php');
try {
    require $folder.'/bootstrap.php';
    putenv('INVENTORY_URL=http://inventory:8080');
    putenv('UI_ALLOWED_UPSTREAM_HOSTS=inventory');
    $settings=ui_settings();
    if (($settings['INVENTORY_URL'] ?? '')!=='http://inventory:8080') throw new RuntimeException('Environment URL was ignored.');
    if (($settings['UI_ALLOWED_UPSTREAM_HOSTS'] ?? '')!=='inventory') throw new RuntimeException('Environment allow-list was ignored.');
    putenv('INVENTORY_URL=http://untrusted:8080');
    $rejected=false;
    try {upstream('inventory','GET','/health');} catch (RuntimeException $e) {$rejected=true;}
    if (!$rejected) throw new RuntimeException('Unapproved host was accepted.');
    echo "PASS: environment-only URLs, environment allow-list and rejected unapproved host.\n";
} finally {
    unlink($folder.'/bootstrap.php');rmdir($folder);
}
