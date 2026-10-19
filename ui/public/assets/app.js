'use strict';

const $ = id => document.getElementById(id);
const services = [['inventory', 'Python'], ['reservation', 'Python'], ['payment', 'PHP'], ['notification', 'PHP']];
const csrf = document.querySelector('meta[name="csrf-token"]').content;
let rooms = [];
let selectedStock = null;
let lastAttempt = null;
let retryAttempt = null;
let roomAttempt = null;
let bookingBusy = false;
let servicesReady = null;
let availabilityVersion = 0;
let inspectionVersion = 0;
let pollTimer = null;
let pollsRemaining = 60;
const bookingErrors = new Map();

function message(text, error = false) {
    $('message').hidden = false;
    $('message').textContent = text;
    $('message').className = 'message' + (error ? ' error' : '');
}

function showPage(name, focus = false) {
    for (const page of ['booking', 'tests']) {
        const selected = page === name;
        $('page-' + page).hidden = !selected;
        $('tab-' + page).classList.toggle('active', selected);
        $('tab-' + page).setAttribute('aria-selected', String(selected));
        $('tab-' + page).tabIndex = selected ? 0 : -1;
    }
    if (focus) $('tab-' + name).focus();
}

function escapeText(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
}

function money(minor, currency = 'INR') {
    return new Intl.NumberFormat('en-IN', {style: 'currency', currency, maximumFractionDigits: 2}).format(minor / 100);
}

function formatDate(value) {
    if (!value) return 'Choose a date';
    return new Date(value + 'T12:00:00').toLocaleDateString('en-IN', {day: 'numeric', month: 'short', year: 'numeric'});
}

function errorText(result) {
    return result.body?.error?.message || 'The request could not be completed. Check Service tests for the response.';
}

function raw(result) {
    $('raw').textContent = JSON.stringify(result, null, 2);
}

async function call(action, extra = {}, show = true) {
    const response = await fetch('/api.php', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
        body: JSON.stringify({action, ...extra}),
    });
    const result = await response.json();
    if (!response.ok || !result.body) throw new Error(result.error || 'The page could not read the service response.');
    if (show) raw(result);
    return result;
}

function updateBookButton() {
    const available = selectedStock && selectedStock.available > 0;
    $('replay').disabled = !lastAttempt || bookingBusy;
    $('conflict').disabled = !lastAttempt || bookingBusy;
    $('book-button').disabled = bookingBusy || (!retryAttempt && (!available || servicesReady === false));
    $('book-button').textContent = bookingBusy ? 'Booking your room…' : retryAttempt ? 'Retry same booking' : 'Confirm booking';
    $('book-help').textContent = retryAttempt ? 'The last response was not received. This safely repeats that same request.' :
        servicesReady === false ? 'A service needs attention. Open View services, then refresh its status.' :
        available ? 'This creates one new booking with a demo payment.' :
        selectedStock?.available === 0 ? 'Sold out for this date. Choose another room or add sample rooms.' : 'Choose an available room to continue.';
}

function updatePreview() {
    const room = rooms.find(item => item.room_type_id === $('room-select').value);
    $('stay-title').textContent = room ? room.name : 'Choose your room';
    $('price-preview').textContent = room ? money(room.price_minor, room.currency) : '—';
    $('stay-preview').textContent = formatDate($('stay-date').value);
    $('setup-date').textContent = 'Rooms will be added for ' + formatDate($('stay-date').value) + '.';
}

async function health() {
    try {
        const result = await call('health', {}, false);
        let healthyCount = 0;
        $('health-cards').innerHTML = services.map(([name, language]) => {
            const item = result.body.services[name];
            const ok = item?.status === 200 && item.body?.status === 'ok';
            if (ok) healthyCount++;
            return `<div class="health-card"><span class="dot ${ok ? 'ok' : 'bad'}"></span><strong>${name[0].toUpperCase() + name.slice(1)}</strong><small>${language} · ${ok ? 'Healthy' : 'Unavailable'}</small></div>`;
        }).join('');
        servicesReady = healthyCount === 4;
        $('system-status').textContent = servicesReady ? 'All services ready for booking' : `${healthyCount} of 4 services ready. Check the service terminals.`;
        $('system-status').className = servicesReady ? 'ready' : 'attention';
    } catch (error) {
        servicesReady = false;
        $('system-status').textContent = 'Could not check services. Open View services and refresh.';
        $('system-status').className = 'attention';
        message(error.message, true);
    }
    updateBookButton();
}

async function loadRooms(selectedRoom = null) {
    const result = await call('rooms', {}, false);
    if (result.status !== 200) throw new Error(errorText(result));
    rooms = result.body.room_types;
    // The listing has a limit. A newly created room must remain selectable even when it falls beyond that limit.
    if (selectedRoom && !rooms.some(room => room.room_type_id === selectedRoom.room_type_id)) rooms.unshift(selectedRoom);
    const keep = selectedRoom?.room_type_id || $('room-select').value;
    $('room-select').innerHTML = '<option value="">' + (rooms.length ? 'Choose a room' : 'No rooms yet — click Add sample rooms') + '</option>' + rooms.map(room =>
        `<option value="${escapeText(room.room_type_id)}">${escapeText(room.name)} · ${escapeText(money(room.price_minor, room.currency))}</option>`
    ).join('');
    if (rooms.some(room => room.room_type_id === keep)) $('room-select').value = keep;
    updatePreview();
}

async function availability(show = false) {
    const version = ++availabilityVersion;
    const room = $('room-select').value;
    const day = $('stay-date').value;
    selectedStock = null;
    updatePreview();
    updateBookButton();
    $('availability-box').className = 'availability';
    if (!room || !day || !$('stay-date').validity.valid) {
        $('stock').textContent = 'Choose a room and a future date';
        $('stock-help').textContent = 'Add sample rooms if you are starting a new demonstration.';
        return;
    }
    $('stock').textContent = 'Checking rooms…';
    const result = await call('availability', {room_type_id: room, stay_date: day}, false);
    if (version !== availabilityVersion) return;
    if (show) raw(result);
    if (result.status === 200) {
        selectedStock = result.body;
        const soldOut = selectedStock.available === 0;
        $('stock').textContent = soldOut ? 'Sold out for this date · 0 of ' + selectedStock.capacity + ' rooms available' :
            `${selectedStock.available} of ${selectedStock.capacity} rooms available`;
        $('stock-help').textContent = soldOut ? 'Choose another room or add a new sample room type.' : 'Each confirmed booking uses one room.';
        $('availability-box').className = 'availability ' + (soldOut ? 'sold-out' : 'available');
    } else {
        $('stock').textContent = result.status === 404 ? 'No rooms set up for this date' : 'Availability could not be checked';
        $('stock-help').textContent = result.status === 404 ? 'Choose the date used when creating these rooms, or add sample rooms for this date.' : errorText(result);
    }
    updateBookButton();
}

function renderBooking(booking) {
    const cancelled = booking.status === 'CANCELLED';
    const confirmed = booking.status === 'CONFIRMED';
    const failure = bookingErrors.get(booking.booking_id);
    $('booking-status').textContent = booking.status;
    $('booking-status').className = 'status ' + (cancelled ? 'cancelled' : confirmed ? '' : 'pending');
    $('result-title').textContent = confirmed ? 'Booking confirmed' : cancelled ? 'Booking cancelled' : 'Your booking is being processed';
    $('result-description').textContent = confirmed ? 'Your room is booked. Keep the booking ID below.' :
        cancelled && failure?.code === 'PAYMENT_DECLINED' ? 'The demo payment was declined. The held room has been released.' :
        cancelled && failure?.code === 'NO_AVAILABILITY' ? 'No room was available when this request reached the service. Choose another room or add sample rooms.' :
        cancelled ? 'This booking was not completed. Open Service tests to inspect the response and recorded workflow.' :
        'Please wait. We are checking the current result automatically. Use Refresh this booking if you return later.';
    const payment = confirmed || booking.status === 'PAID' ? 'Demo payment successful' : cancelled ? 'Not completed — see payment record' : 'Processing';
    const notification = booking.notification_status === 'SENT' ? 'Demo notification sent' : cancelled ? 'Not sent' : 'Pending';
    $('summary').innerHTML = [
        ['Check-in', formatDate(booking.stay_date)],
        ['Booking total', booking.amount_minor != null ? money(booking.amount_minor, booking.currency) : 'Not set'],
        ['Payment', payment], ['Notification', notification],
    ].map(([label, value]) => `<div><span class="label">${escapeText(label)}</span><strong>${escapeText(value)}</strong></div>`).join('');
    $('receipt-id').hidden = false;
    $('inspector-booking').textContent = 'Current booking: ' + booking.booking_id + ' · ' + booking.status;
}

function trackBooking(bookingId) {
    clearTimeout(pollTimer);
    inspectionVersion++;
    pollsRemaining = 60;
    $('booking-id').value = bookingId;
}

async function inspect(show = true, expectedId = null) {
    const bid = $('booking-id').value.trim();
    if (!bid || (expectedId && expectedId !== bid)) return;
    const version = ++inspectionVersion;
    clearTimeout(pollTimer);
    const result = await call('booking', {booking_id: bid}, false);
    if (version !== inspectionVersion || bid !== $('booking-id').value.trim()) return;
    if (show) raw(result);
    if (result.status !== 200) {message(errorText(result), true); return false;}
    renderBooking(result.body);
    const steps = await call('steps', {booking_id: bid}, false);
    if (version !== inspectionVersion || bid !== $('booking-id').value.trim()) return;
    $('timeline').innerHTML = (steps.body.steps || []).map(step => `<li>${escapeText(step.to_state)}</li>`).join('');
    await availability(false);
    if (version !== inspectionVersion) return;
    const complete = result.body.status === 'CANCELLED' || (result.body.status === 'CONFIRMED' && result.body.notification_status === 'SENT');
    if (!complete && pollsRemaining-- > 0) {
        pollTimer = setTimeout(() => inspect(false, bid).catch(error => message('Could not refresh this booking. ' + error.message, true)), 1500);
    } else if (!complete) {
        $('result-description').textContent = 'This booking is still processing. Check the service terminals, then use Refresh this booking. Reuse the original request to retry safely.';
    }
    return true;
}

async function submitBooking(attempt, replay = false) {
    let result;
    try {
        result = await call('book', attempt, true);
    } catch (error) {
        // A missing response does not prove the booking failed. Preserve the key before offering a retry.
        retryAttempt = attempt;
        throw new Error('We could not read the booking result. Click Retry same booking to check it safely. ' + error.message);
    }
    retryAttempt = null;
    const bid = result.body.booking_id || result.body.error?.details?.booking_id;
    if (bid) {
        if (result.body.error) bookingErrors.set(bid, result.body.error);
        trackBooking(bid);
        try {await inspect(false);} catch (error) {message('The booking response was received. Use Refresh this booking to check its current status. ' + error.message, true);}
    } else {
        trackBooking('');
        $('receipt-id').hidden = true;
        $('summary').textContent = '';
        $('timeline').textContent = '';
        $('booking-status').textContent = 'NOT CREATED';
        $('booking-status').className = 'status cancelled';
        $('result-title').textContent = 'Booking not created';
        $('result-description').textContent = errorText(result);
        $('inspector-booking').textContent = 'This response did not contain a booking ID.';
    }
    if (result.status >= 400) {
        message(result.body.error?.code === 'NO_AVAILABILITY' ? 'The room became unavailable. Choose another room or add sample rooms.' : `HTTP ${result.status}: ${errorText(result)}`, true);
    } else if (replay) {
        message('Original request replayed. Its original response is shown in Service tests; no extra booking was requested.');
    } else if (result.status === 202) {
        message('Booking accepted. Please wait while the current payment and booking status refresh.');
    } else {
        message('Booking confirmed. Your confirmation and booking ID appear under Your booking.');
    }
    raw(result); // Preserve the original POST response, including HTTP 202, while GET polling continues.
    return result;
}

function guarded(handler) {
    return async event => {
        event.preventDefault();
        const button = event.submitter || event.currentTarget;
        const canDisable = 'disabled' in button;
        if (canDisable) button.disabled = true;
        try {await handler(event);} catch (error) {message(error.message, true);} finally {
            if (canDisable) button.disabled = false;
            updateBookButton();
        }
    };
}

async function createRooms() {
    if (!$('stay-date').reportValidity()) {showPage('booking'); return;}
    if (!$('room-form').checkValidity()) {
        showPage('tests'); $('room-setup').open = true; $('room-form').reportValidity(); return;
    }
    const payload = {name: $('room-name').value.trim(), capacity: Number($('capacity').value), price_minor: Number($('price').value) * 100, currency: 'INR', dates: [$('stay-date').value]};
    if (!payload.name) throw new Error('Enter a room name in Service tests → Room setup.');
    if (!roomAttempt || JSON.stringify(roomAttempt.payload) !== JSON.stringify(payload)) roomAttempt = {key: crypto.randomUUID(), payload};
    const result = await call('create_room', roomAttempt);
    if (result.status !== 201) throw new Error(errorText(result));
    roomAttempt = null;
    await loadRooms(result.body);
    await availability(false);
    showPage('booking');
    message(`${result.body.capacity} sample rooms added for ${formatDate($('stay-date').value)} at ${money(result.body.price_minor)} each. You can now confirm a booking.`);
}

function updateScenario() {
    const notes = [];
    if ($('payment-mode').value === 'decline') notes.push('Test selected: payment will be declined and the held room released.');
    if ($('payment-mode').value === 'slow_success') notes.push('Test selected: payment will be slow. Wait for the booking status to refresh.');
    if ($('notification-mode').value === 'fail_once') notes.push('Notification will fail once and then retry.');
    $('scenario-banner').hidden = notes.length === 0;
    $('scenario-banner').textContent = notes.join(' ');
}

for (const name of ['booking', 'tests']) {
    $('tab-' + name).addEventListener('click', () => showPage(name));
    $('tab-' + name).addEventListener('keydown', event => {
        if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
            event.preventDefault();
            showPage(event.key === 'Home' ? 'booking' : event.key === 'End' ? 'tests' : name === 'booking' ? 'tests' : 'booking', true);
        }
    });
}
$('open-services').addEventListener('click', () => showPage('tests', true));
$('back-to-booking').addEventListener('click', () => showPage('booking', true));
$('use-scenario').addEventListener('click', () => {updateScenario(); showPage('booking', true);});
$('reset-scenarios').addEventListener('click', () => {
    $('payment-mode').value = 'success'; $('notification-mode').value = 'success'; updateScenario(); message('Normal payment and notification selected for the next new booking.');
});
$('payment-mode').addEventListener('change', updateScenario);
$('notification-mode').addEventListener('change', updateScenario);
$('add-sample').addEventListener('click', guarded(createRooms));
$('room-form').addEventListener('submit', guarded(createRooms));
$('booking-form').addEventListener('submit', guarded(async () => {
    if (bookingBusy) return;
    if (!retryAttempt && (!selectedStock || selectedStock.available <= 0)) throw new Error('Choose an available room or add sample rooms first.');
    if (!retryAttempt && !$('guest').value.trim()) throw new Error('Enter a guest name or reference.');
    bookingBusy = true;
    updateBookButton();
    clearTimeout(pollTimer);
    inspectionVersion++;
    const repeating = Boolean(retryAttempt);
    lastAttempt = retryAttempt || {key: crypto.randomUUID(), payload: {
        room_type_id: $('room-select').value, stay_date: $('stay-date').value,
        guest_ref: $('guest').value.trim(), recipient: $('recipient').value.trim(),
        payment_mode: $('payment-mode').value, notification_mode: $('notification-mode').value,
    }};
    $('replay').disabled = false;
    $('conflict').disabled = false;
    $('last-request-label').textContent = 'Last booking request: ' + lastAttempt.payload.guest_ref + ' · ' + formatDate(lastAttempt.payload.stay_date) + '. Replay uses these original details.';
    message(repeating ? 'Checking the same booking request safely…' : 'Booking your room. Please wait for the confirmation.');
    try {await submitBooking(lastAttempt, repeating);} finally {bookingBusy = false;}
}));
$('lookup-form').addEventListener('submit', guarded(async () => {
    const bid = $('lookup-id').value.trim();
    if (!/^[0-9a-f-]{36}$/i.test(bid)) throw new Error('Paste the full booking ID, including its hyphens.');
    const previousId = $('booking-id').value;
    trackBooking(bid);
    try {
        const found = await inspect(true);
        if (!found) trackBooking(previousId);
    } catch (error) {trackBooking(previousId); throw error;}
}));
$('refresh-booking').addEventListener('click', guarded(async () => {pollsRemaining = 60; await inspect(true);}));
$('replay').addEventListener('click', guarded(async () => {
    bookingBusy = true; updateBookButton();
    try {await submitBooking(lastAttempt, true);} finally {bookingBusy = false;}
}));
$('conflict').addEventListener('click', guarded(async () => {
    const changedGuest = lastAttempt.payload.guest_ref === 'conflict-demo' ? 'changed-demo' : 'conflict-demo';
    const result = await call('book', {key: lastAttempt.key, payload: {...lastAttempt.payload, guest_ref: changedGuest}});
    message(result.status === 409 ? 'HTTP 409: changed payload rejected for the same request key. This is the expected conflict result.' : `HTTP ${result.status}: inspect the API response.`, result.status !== 409);
}));
$('check-stock').addEventListener('click', guarded(() => availability(true)));
$('room-select').addEventListener('change', () => availability(false).catch(error => message(error.message, true)));
$('stay-date').addEventListener('change', () => availability(false).catch(error => message(error.message, true)));
$('refresh-health').addEventListener('click', guarded(health));
for (const name of ['payment', 'notification']) {
    $('inspect-' + name).addEventListener('click', guarded(async () => {
        const bid = $('booking-id').value.trim();
        if (!bid) throw new Error('Make or find a booking first.');
        const result = await call(name, {booking_id: bid});
        message(result.status >= 400 ? errorText(result) : 'The ' + name + ' response is shown below.', result.status >= 400);
        $('raw-details').open = true;
    }));
}

const tomorrow = new Date();
tomorrow.setDate(tomorrow.getDate() + 1);
const localDate = date => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
$('stay-date').min = localDate(tomorrow);
const defaultDate = new Date();
defaultDate.setDate(defaultDate.getDate() + 7);
$('stay-date').value = localDate(defaultDate);
updatePreview();
updateScenario();
health();
loadRooms().catch(error => {
    $('room-select').innerHTML = '<option value="">Rooms could not be loaded</option>';
    message('Rooms could not be loaded. Check Inventory in Service tests, then refresh the page. ' + error.message, true);
});
