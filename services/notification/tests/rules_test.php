<?php
declare(strict_types=1);
namespace CampusStay;
require __DIR__.'/../src/platform.php';
require __DIR__.'/../src/rules.php';
$results=[];
foreach (['PENDING','PAID','CANCELLED'] as $state) {
    try { require_confirmed($state);throw new \RuntimeException('Unconfirmed booking accepted'); }
    catch (BusinessError $error) { if ($error->status!==409) throw new \RuntimeException('Wrong error'); }
    $results[]='BR8 rejects '.$state;
}
require_confirmed('CONFIRMED');$results[]='BR8 accepts CONFIRMED';
echo json_encode(['service'=>'notification','language'=>'PHP','tests'=>count($results),'failures'=>0,'cases'=>$results],JSON_PRETTY_PRINT|JSON_THROW_ON_ERROR)."\n";
