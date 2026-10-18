<?php
declare(strict_types=1);
if (parse_url($_SERVER['REQUEST_URI'],PHP_URL_PATH)==='/health') {
    header('Content-Type: application/json');echo json_encode(['status'=>'ok','service'=>'ui']);exit;
}
require __DIR__.'/../bootstrap.php';
ui_session();$csrf=$_SESSION['csrf'];session_write_close();
header("Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'");
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');
?><!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="csrf-token" content="<?=htmlspecialchars($csrf,ENT_QUOTES,'UTF-8')?>">
<title>CampusStay | Guesthouse booking lab</title><link rel="stylesheet" href="/assets/style.css"><script src="/assets/app.js" defer></script></head>
<body><header class="topbar"><a class="brand" href="/"><span class="mark">CS</span><span>CampusStay<small>Guesthouse booking lab</small></span></a><span class="tag">Local demonstration · Mock payments</span></header>
<main><section class="intro"><div><p class="eyebrow">A CAMPUS VISIT, ONE ROOM, ONE NIGHT</p><h1>Make a booking.<br>See the services work together.</h1><p>Reserve a guesthouse room for a campus visit. Explore a successful booking, a declined payment, or a slow response with safe recovery.</p></div><aside class="scope"><strong>Four services. One booking.</strong><p>Inventory and Reservation run in Python.<br>Payment and Notification run in PHP.</p><span>Each service keeps its own database.</span></aside></section>
<section aria-label="Service health" class="service-strip"><div id="health-cards" class="health-grid"></div><button id="refresh-health" class="button secondary small" type="button">Refresh service status</button></section>
<div id="message" class="message" role="status" hidden></div>
<section class="workspace"><article class="panel"><div class="panel-heading"><span class="step">01</span><div><h2>Prepare a stay</h2><p>Create a small, separate inventory for your demonstration.</p></div></div>
<form id="room-form"><label for="room-name">Room type</label><input id="room-name" value="Campus visitor room" maxlength="80" required>
<div class="form-row"><div><label for="capacity">Rooms available</label><input id="capacity" type="number" min="1" max="1000" value="5" required></div><div><label for="price">Price per night (INR)</label><input id="price" type="number" min="1" step="1" value="2500" required></div></div>
<label for="stay-date">Stay date</label><input id="stay-date" type="date" required>
<button class="button primary" type="submit">Create demo inventory</button></form>
<div class="availability"><div><span class="muted">Selected availability</span><strong id="stock">Choose or create inventory</strong></div><button class="button secondary small" id="check-stock" type="button">Check</button></div>
</article><article class="panel"><div class="panel-heading"><span class="step">02</span><div><h2>Book a room</h2><p>The room price is supplied by Inventory.</p></div></div>
<form id="booking-form"><label for="room-select">Available room types</label><select id="room-select" required><option value="">Create inventory first</option></select>
<div class="form-row"><div><label for="guest">Guest reference</label><input id="guest" value="campus-visitor-01" maxlength="80" required></div><div><label for="recipient">Demo recipient</label><input id="recipient" type="email" value="visitor@example.test" required></div></div>
<div class="form-row"><div><label for="payment-mode">Payment scenario</label><select id="payment-mode"><option value="success">Successful payment</option><option value="decline">Declined payment</option><option value="slow_success">Slow successful payment</option></select></div><div><label for="notification-mode">Notification scenario</label><select id="notification-mode"><option value="success">Successful notification</option><option value="fail_once">Fail once, then retry</option></select></div></div>
<button class="button primary" type="submit">Book room</button><p class="help">Every new booking gets a new request key. Use Replay below to repeat the exact original request safely.</p></form>
</article></section>
<section class="panel result-panel"><div class="result-heading"><div><p class="eyebrow">BOOKING INSPECTOR</p><h2>Follow the outcome</h2></div><span id="booking-status" class="status neutral">No booking yet</span></div>
<form id="lookup-form" class="lookup"><label class="sr-only" for="booking-id">Booking ID</label><input id="booking-id" placeholder="Booking ID appears here, or paste an existing one" required><button class="button secondary" type="submit">Refresh booking</button></form>
<div id="summary" class="summary"><p class="muted">Your booking result and recorded workflow steps will appear here.</p></div><ol id="timeline" class="timeline"></ol>
<div class="actions"><button id="replay" class="button secondary small" type="button" disabled>Replay original request</button><button id="conflict" class="button secondary small" type="button" disabled>Test changed-payload conflict</button><button id="inspect-payment" class="button text small" type="button">Inspect payment</button><button id="inspect-notification" class="button text small" type="button">Inspect notification</button></div>
<details class="technical"><summary>Inspect the last API response</summary><pre id="raw">No API request yet.</pre></details></section>
<footer>CampusStay is an API demonstration for Scalable Services. No real payment or email is sent. Use the terminal scripts for the required challenge evidence.</footer></main></body></html>
