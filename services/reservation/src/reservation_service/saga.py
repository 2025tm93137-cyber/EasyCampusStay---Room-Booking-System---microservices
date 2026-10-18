"""Durable saga. Only HTTP touches other services; all SQL is reservation-local."""
import os
import httpx
from . import repository
from .platform import BusinessError, database, log
from .rules import may_release_after_payment


class UncertainDependency(Exception):
    pass


def call(service, path, key, correlation_id, payload=None):
    url = os.environ[service.upper() + '_URL'].rstrip('/') + path
    timeout = float(os.getenv('HTTP_TIMEOUT_SECONDS', '1'))
    try:
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            response = client.post(url, json=payload, headers={
                'Idempotency-Key': key, 'X-Correlation-ID': correlation_id,
            })
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        log('dependency_uncertain', correlation_id, dependency=service, reason=type(exc).__name__)
        raise UncertainDependency(service) from exc
    if response.status_code >= 500:
        log('dependency_uncertain', correlation_id, dependency=service, status=response.status_code)
        raise UncertainDependency(service)
    if response.status_code >= 400:
        error = body.get('error', {})
        raise BusinessError(response.status_code, error.get('code','DEPENDENCY_REJECTED'),
                            error.get('message','A dependency rejected the request.'), error.get('details'))
    return body


def pending(booking_id):
    return 202, repository.response_body(repository.read(booking_id))


def deliver_notification(row, cid):
    if row['notification_status'] == 'SENT':
        return
    bid = str(row['id'])
    payload = row['request_body']
    try:
        notification = call('notification', '/api/v1/notifications', bid + ':notify', cid, {
            'booking_id': bid, 'recipient': payload['recipient'], 'booking_state': 'CONFIRMED',
            'simulation': payload['notification_mode'],
        })
        if notification['status'] == 'FAILED':
            notification = call('notification', f'/api/v1/notifications/{bid}/retry', bid + ':notify-retry', cid)
        if notification['status'] == 'SENT':
            repository.notification_sent(row['id'])
    except (UncertainDependency, BusinessError):
        log('notification_deferred', cid, booking_id=bid)


def run(booking_id, correlation_id):
    """One owner advances a booking; retries always reuse downstream operation keys.

    The session advisory lock is held on an AUTOCOMMIT connection, so no database
    transaction stays open while an HTTP call is made. A process exit releases it.
    """
    bid = str(booking_id)
    with database(autocommit=True) as lock_conn:
        acquired = lock_conn.try_lock('saga:' + bid)
        if not acquired:
            return None
        try:
            result = advance(booking_id, correlation_id)
            repository.cache_response(booking_id, *result)
            return result
        finally:
            lock_conn.release_lock('saga:' + bid)


def advance(booking_id, cid):
    bid = str(booking_id)
    row = repository.read(booking_id)
    payload = row['request_body']
    if row['status'] == 'PENDING':
        try:
            hold = call('inventory', '/api/v1/holds', bid + ':hold', cid, {
                'booking_id': bid, 'room_type_id': payload['room_type_id'], 'stay_date': payload['stay_date'],
            })
        except UncertainDependency:
            return pending(booking_id)
        except BusinessError as exc:
            row = repository.transition(booking_id, 'CANCELLED', failure_status=exc.status, failure_body=exc.body())
        else:
            row = repository.transition(booking_id, 'RESERVED', amount_minor=hold['amount_minor'], currency=hold['currency'])
            log('room_reserved', cid, booking_id=bid)

    if row['status'] == 'RESERVED':
        row = repository.transition(booking_id, 'PAYMENT_PENDING')

    if row['status'] in {'PAYMENT_PENDING', 'PAYMENT_UNCERTAIN'}:
        try:
            payment = call('payment', '/api/v1/payments', bid + ':charge', cid, {
                'booking_id': bid, 'amount_minor': row['amount_minor'], 'currency': row['currency'],
                'simulation': payload['payment_mode'],
            })
        except UncertainDependency:
            if row['status'] == 'PAYMENT_PENDING':
                repository.transition(booking_id, 'PAYMENT_UNCERTAIN')
            return pending(booking_id)
        except BusinessError as exc:
            row = repository.transition(booking_id, 'COMPENSATING', failure_status=exc.status, failure_body=exc.body())
            log('payment_rejected', cid, booking_id=bid, code=exc.code)
        else:
            if payment['status'] != 'CHARGED':
                # A refund observed unexpectedly cannot confirm a booking.
                exc = BusinessError(409, 'PAYMENT_NOT_CHARGED', 'The payment is not charged.')
                row = repository.transition(booking_id, 'COMPENSATING', failure_status=exc.status, failure_body=exc.body())
            else:
                row = repository.transition(booking_id, 'PAID', payment_id=payment['id'])

    if row['status'] == 'PAID':
        try:
            call('inventory', f'/api/v1/holds/{bid}/confirm', bid + ':confirm', cid)
        except UncertainDependency:
            return pending(booking_id)
        except BusinessError as exc:
            row = repository.transition(booking_id, 'COMPENSATING', failure_status=exc.status, failure_body=exc.body())
        else:
            row = repository.transition(booking_id, 'CONFIRMED')
            log('booking_confirmed', cid, booking_id=bid)

    if row['status'] == 'COMPENSATING':
        refunded = False
        try:
            if row['payment_id']:
                payment = call('payment', f'/api/v1/payments/{bid}/refund', bid + ':refund', cid)
                refunded = payment['status'] == 'REFUNDED'
            may_release_after_payment(row['payment_id'] is not None, refunded)
            call('inventory', f'/api/v1/holds/{bid}/release', bid + ':release', cid)
        except (UncertainDependency, BusinessError):
            log('compensation_pending', cid, booking_id=bid)
            return pending(booking_id)
        row = repository.transition(booking_id, 'CANCELLED')
        log('compensation_completed', cid, booking_id=bid)

    if row['status'] == 'CONFIRMED':
        deliver_notification(row, cid)
        return 201, repository.response_body(repository.read(booking_id))
    if row['status'] == 'CANCELLED':
        body = row['failure_body'] or BusinessError(409, 'BOOKING_CANCELLED', 'The booking was cancelled.').body()
        body['error']['details'] = {**(body['error'].get('details') or {}), 'booking_id': bid}
        return row['failure_status'] or 409, body
    return pending(booking_id)
