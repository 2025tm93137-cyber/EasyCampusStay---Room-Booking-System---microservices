from uuid import uuid4
from datetime import date
from .mysql import json_document
from .platform import BusinessError, database, fingerprint, require_same_payload, validate_key
from .rules import require_transition, valid_stay_date


def claim(key: str, payload: dict, correlation_id: str):
    validate_key(key)
    digest = fingerprint(payload)
    booking_id = uuid4()
    with database() as conn:
        conn.lock('booking-request:' + key)
        row = conn.execute("SELECT * FROM idempotency_records WHERE scope='bookings:create' AND idem_key=%s", (key,)).fetchone()
        if row is None:
            valid_stay_date(date.fromisoformat(payload['stay_date']))
            conn.execute('INSERT INTO bookings(id,room_type_id,stay_date,request_body,status,correlation_id) '
                         "VALUES (%s,%s,%s,%s,'PENDING',%s)",
                         (booking_id, payload['room_type_id'], payload['stay_date'], json_document(payload), correlation_id))
            conn.execute('INSERT INTO idempotency_records(scope,idem_key,fingerprint,booking_id) '
                         "VALUES ('bookings:create',%s,%s,%s)", (key, digest, booking_id))
            conn.execute("INSERT INTO booking_steps(booking_id,from_state,to_state) VALUES (%s,NULL,'PENDING')", (booking_id,))
            return booking_id, None
        require_same_payload(row['fingerprint'], digest)
        cached = (row['http_status'], row['response_body']) if row['http_status'] is not None else None
        return row['booking_id'], cached


def read(booking_id):
    with database() as conn:
        row = conn.execute('SELECT * FROM bookings WHERE id=%s', (booking_id,)).fetchone()
    if not row:
        raise BusinessError(404, 'BOOKING_NOT_FOUND', 'The booking does not exist.')
    return row


def response_body(row):
    return {
        'booking_id': str(row['id']), 'status': row['status'],
        'room_type_id': str(row['room_type_id']), 'stay_date': str(row['stay_date']),
        'amount_minor': row['amount_minor'], 'currency': row['currency'],
        'payment_id': str(row['payment_id']) if row['payment_id'] else None,
        'notification_status': row['notification_status'],
    }


def transition(booking_id, target, **changes):
    allowed = {'amount_minor', 'currency', 'payment_id', 'failure_status', 'failure_body'}
    if not set(changes).issubset(allowed):
        raise ValueError('Unsupported booking update')
    with database() as conn:
        row = conn.execute('SELECT * FROM bookings WHERE id=%s FOR UPDATE', (booking_id,)).fetchone()
        require_transition(row['status'], target)
        if row['status'] == target:
            return row
        values = [target]
        assignments = ['status=%s', 'updated_at=NOW()']
        for name, value in changes.items():
            assignments.append(name + '=%s')
            values.append(json_document(value) if name == 'failure_body' else value)
        values.append(booking_id)
        conn.execute('UPDATE bookings SET ' + ','.join(assignments) + ' WHERE id=%s', values)
        conn.execute('INSERT INTO booking_steps(booking_id,from_state,to_state) VALUES (%s,%s,%s)',
                     (booking_id, row['status'], target))
    return read(booking_id)


def notification_sent(booking_id):
    with database() as conn:
        conn.execute("UPDATE bookings SET notification_status='SENT',updated_at=NOW() WHERE id=%s AND status='CONFIRMED'", (booking_id,))


def cache_response(booking_id, status, body):
    # A 202 acceptance is also cached permanently. Later progress is read via GET;
    # repeating POST returns exactly the original status/body, even after recovery.
    with database() as conn:
        conn.execute('UPDATE idempotency_records SET http_status=%s,response_body=%s '
                     'WHERE booking_id=%s AND http_status IS NULL', (status, json_document(body), booking_id))


def cached_response(booking_id):
    with database() as conn:
        row = conn.execute('SELECT http_status,response_body FROM idempotency_records WHERE booking_id=%s', (booking_id,)).fetchone()
    return (row['http_status'], row['response_body']) if row['http_status'] is not None else None


def recovery_candidates():
    with database() as conn:
        return conn.execute("SELECT id,correlation_id FROM bookings WHERE status NOT IN ('CANCELLED','CONFIRMED') "
                            "OR (status='CONFIRMED' AND notification_status='PENDING') ORDER BY updated_at LIMIT 50").fetchall()


def steps(booking_id):
    with database() as conn:
        return conn.execute('SELECT from_state,to_state,created_at FROM booking_steps WHERE booking_id=%s ORDER BY id', (booking_id,)).fetchall()
