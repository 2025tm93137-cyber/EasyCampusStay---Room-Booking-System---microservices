<?php
declare(strict_types=1);
namespace CampusStay;
require __DIR__.'/../src/platform.php';
require __DIR__.'/../src/rules.php';
$results=[];
foreach ([-1,0,1.5,true,'100'] as $index=>$amount) {
    try { require_positive_amount($amount);throw new \RuntimeException('Invalid amount accepted'); }
    catch (BusinessError $error) { if ($error->status!==422) throw new \RuntimeException('Wrong error'); }
    $results[]='BR6 rejects invalid amount case '.($index+1);
}
foreach ([1,250000] as $amount) { require_positive_amount($amount);$results[]='BR6 accepts integer '.$amount; }
try { require_refundable('DECLINED');throw new \RuntimeException('Declined payment was refundable'); }
catch (BusinessError $error) { if ($error->status!==409) throw new \RuntimeException('Wrong error'); }
$results[]='BR7 rejects refund of declined payment';
foreach (['CHARGED','REFUNDED'] as $state) { require_refundable($state);$results[]='BR7 accepts '.$state; }
echo json_encode(['service'=>'payment','language'=>'PHP','tests'=>count($results),'failures'=>0,'cases'=>$results],JSON_PRETTY_PRINT|JSON_THROW_ON_ERROR)."\n";
