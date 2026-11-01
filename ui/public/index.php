<?php
declare(strict_types=1);
if (parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) === '/health') {
    header('Content-Type: application/json');
    echo json_encode(['status' => 'ok', 'service' => 'ui']);
    exit;
}
require __DIR__.'/../bootstrap.php';
ui_session();
$csrf = $_SESSION['csrf'];
session_write_close();
header("Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'");
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');
?><!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="<?=htmlspecialchars($csrf, ENT_QUOTES, 'UTF-8')?>">
    <title>Easy Campus Stay | A simple room-booking system</title>
    <link rel="stylesheet" href="/assets/style.css?v=easystay-1">
    <script src="/assets/app.js?v=easystay-1" defer></script>
</head>
<body>
<header class="topbar">
    <a class="brand" href="/" aria-label="Easy Campus Stay home"><span class="brand-mark">es<span>.</span></span><span>Easy Campus Stay<small>A simple room-booking system</small></span></a>
    <span class="demo-badge"><span class="dot"></span> Practice booking · Demo payments</span>
</header>
<main>
    <nav class="tabs" role="tablist" aria-label="Choose a page">
        <button id="tab-booking" class="tab active" type="button" role="tab" aria-selected="true" aria-controls="page-booking">Book a room</button>
        <button id="tab-tests" class="tab" type="button" role="tab" aria-selected="false" aria-controls="page-tests" tabindex="-1">Service tests</button>
    </nav>
    <div id="message" class="message" role="status" aria-live="polite" hidden></div>

    <section id="page-booking" role="tabpanel" aria-labelledby="tab-booking">
        <section class="intro">
            <div><p class="eyebrow">A ROOM. A NIGHT. ALL SORTED.</p><h1>Your next stay,<br>made easy.</h1><p>Choose a room, add a guest reference, and book.<br class="desktop-break"> We will show you what happens at every step.</p></div>
            <div class="intro-note"><span class="intro-symbol" aria-hidden="true">1</span><div><strong>One room for one night</strong><p>A simple room-booking demo.<br>No real payment or email is sent.</p></div></div>
        </section>
        <div class="system-line"><span id="system-status">Checking booking services…</span><button id="open-services" class="link-button" type="button">View services</button></div>
        <div class="booking-layout">
            <section class="panel booking-panel" aria-labelledby="booking-title">
                <div class="panel-heading"><div><p class="eyebrow">LET’S GET YOU BOOKED</p><h2 id="booking-title">Book your room</h2></div><span class="night-badge">1 night</span></div>
                <form id="booking-form">
                    <fieldset><legend><span class="step">1</span> Choose your stay</legend>
                        <label for="stay-date">Check-in date</label><input id="stay-date" type="date" required aria-describedby="date-help"><p id="date-help" class="help">Your booking is for one night from this date.</p>
                        <label for="room-select">Room type</label><select id="room-select" required><option value="">Loading rooms…</option></select>
                        <div id="availability-box" class="availability"><div><strong id="stock">Choose a room to check availability</strong><p id="stock-help">First time here? Add sample rooms below.</p></div><button id="check-stock" class="link-button" type="button">Refresh</button></div>
                        <div class="sample-row"><span>Need rooms for your demonstration?</span><button id="add-sample" class="button secondary small" type="button">Add sample rooms</button></div>
                    </fieldset>
                    <fieldset><legend><span class="step">2</span> Add your guest details</legend>
                        <label for="guest">Guest name or reference</label><input id="guest" value="demo-guest-01" maxlength="80" required aria-describedby="guest-help"><p id="guest-help" class="help">Use a made-up reference, for example demo-guest-01.</p>
                        <label for="recipient">Demo email address</label><input id="recipient" type="email" value="guest@example.test" maxlength="254" required aria-describedby="email-help"><p id="email-help" class="help">Use an example.test address for this demonstration.</p>
                    </fieldset>
                    <div class="checkout"><span class="step">3</span><div><strong>Ready to book?</strong><p>One click makes one new booking.</p></div></div>
                    <div id="scenario-banner" class="scenario-banner" hidden></div>
                    <button id="book-button" class="button primary" type="submit" disabled>Confirm booking</button>
                    <p id="book-help" class="help centered">Choose an available room to continue.</p>
                </form>
            </section>
            <aside class="stay-column">
                <section class="panel stay-card" aria-labelledby="stay-title"><p class="eyebrow">YOUR STAY</p><h2 id="stay-title">Choose your room</h2><dl class="stay-details"><div><dt>Check-in</dt><dd id="stay-preview">—</dd></div><div><dt>Length of stay</dt><dd>1 night</dd></div><div><dt>Rooms per booking</dt><dd>1 room</dd></div></dl><div class="price-row"><span>Total for this stay</span><strong id="price-preview">—</strong></div><p class="help">The selected room’s price is the total used for the demo payment.</p></section>
                <section id="booking-result" class="panel result-card" aria-labelledby="result-title" aria-live="polite">
                    <p class="eyebrow">YOUR BOOKING</p><span id="booking-status" class="status neutral">No booking yet</span><h2 id="result-title">Your confirmation appears here</h2><p id="result-description" class="muted">After you book, you will see the booking ID, total amount, and notification status.</p><div id="summary" class="summary"></div>
                    <div id="receipt-id" hidden><label for="booking-id">Booking ID</label><input id="booking-id" readonly aria-label="Current booking ID"><p class="help">Keep this ID to check this booking later.</p><button id="refresh-booking" class="button secondary small" type="button">Refresh this booking</button></div>
                </section>
                <details class="panel find-booking"><summary>Already have a booking ID?</summary><form id="lookup-form"><label for="lookup-id">Paste your booking ID</label><input id="lookup-id" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" required><button class="button secondary" type="submit">Find booking</button></form></details>
            </aside>
        </div>
    </section>

    <section id="page-tests" role="tabpanel" aria-labelledby="tab-tests" hidden>
        <section class="tests-intro"><p class="eyebrow">FOR YOUR ASSIGNMENT DEMONSTRATION</p><h1>See how the services work.</h1><p>Make a booking on the first tab. Use this page when you want to inspect it or try a failure scenario.</p></section>
        <section class="panel" aria-labelledby="services-title"><div class="panel-heading"><div><h2 id="services-title">1. Check the four services</h2><p>All four should show Healthy before a normal booking.</p></div><button id="refresh-health" class="button secondary small" type="button">Refresh status</button></div><div id="health-cards" class="health-grid"></div></section>
        <div class="tests-layout">
            <section class="panel" aria-labelledby="scenario-title"><h2 id="scenario-title">2. Choose a booking scenario</h2><p class="muted">These settings apply to the next new booking. Start with successful payment and notification.</p>
                <label for="payment-mode">Demo payment</label><select id="payment-mode"><option value="success">Successful payment (normal booking)</option><option value="decline">Declined payment (room is released)</option><option value="slow_success">Slow successful payment (wait for confirmation)</option></select>
                <label for="notification-mode">Demo notification</label><select id="notification-mode"><option value="success">Successful notification</option><option value="fail_once">Fail once, then retry</option></select>
                <div class="actions"><button id="use-scenario" class="button secondary" type="button">Go to booking</button><button id="reset-scenarios" class="link-button" type="button">Reset to normal</button></div>
                <p class="help">A declined payment should cancel the booking and restore its held room. A slow payment can return HTTP 202 before the booking becomes confirmed.</p>
            </section>
            <section class="panel" aria-labelledby="replay-title"><h2 id="replay-title">3. Repeat the last booking request</h2><p id="last-request-label" class="muted">Make a booking in this browser page first.</p>
                <div class="test-action"><button id="replay" class="button secondary" type="button" disabled>Replay original request</button><p>Repeat the same request and key. Expect the original response and the same booking ID. It should use no extra room.</p></div>
                <div class="test-action"><button id="conflict" class="button secondary" type="button" disabled>Test changed-payload conflict</button><p>Keep the key but change the guest reference. Expect HTTP 409 because the request no longer matches.</p></div>
                <p class="help">“Confirm booking” always starts a new request. Use Replay for the idempotency demonstration.</p>
            </section>
        </div>
        <section class="panel" aria-labelledby="inspect-title"><div class="panel-heading"><div><h2 id="inspect-title">4. Inspect the booking and API response</h2><p id="inspector-booking">No booking selected yet.</p></div><button id="back-to-booking" class="button secondary small" type="button">View booking</button></div><ol id="timeline" class="timeline" aria-label="Recorded booking workflow"></ol><div class="actions"><button id="inspect-payment" class="button secondary small" type="button">Inspect payment</button><button id="inspect-notification" class="button secondary small" type="button">Inspect notification</button></div><details id="raw-details" class="technical" open><summary>Inspect the last API response</summary><p class="help">status is the HTTP status. body contains the service response. A slow request’s original HTTP 202 stays visible while the booking card shows the latest status.</p><pre id="raw">No API request yet.</pre></details></section>
        <details id="room-setup" class="panel setup-panel"><summary>Room setup: change the sample room details</summary><p class="muted">Creates a new room type with stock for the date selected on the booking tab. It does not refill or replace existing rooms.</p><form id="room-form"><div class="form-row"><div><label for="room-name">Room name</label><input id="room-name" value="Easy Campus Stay Deluxe" maxlength="80" required></div><div><label for="capacity">Number of rooms to add</label><input id="capacity" type="number" min="1" max="1000" value="5" required></div><div><label for="price">Price for one night (INR)</label><input id="price" type="number" min="1" step="1" value="2500" required></div></div><p id="setup-date" class="help"></p><button class="button secondary" type="submit">Create these rooms and return to booking</button></form></details>
        <section class="terminal-note"><h2>Steps 23–25 still run in PowerShell</h2><p>The scripted main flow, 20-request concurrency test, and simultaneous idempotency test create their own test inventory and save evidence. The buttons above help explain individual requests.</p><p class="help">Follow EASY_STAY_START_HERE.txt for the commands. Keep the service terminals running.</p></section>
    </section>
    <footer>Easy Campus Stay · Scalable Services assignment · Python and PHP · Local demonstration</footer>
</main>
</body>
</html>
