from uuid import uuid4
from .platform import BusinessError
from .rules import require_capacity, require_confirmable, valid_stay_date

# Create a room type and initialize its inventory for the requested dates.
def create_room_type(conn, payload):
    room_id = uuid4()
    conn.execute('INSERT INTO room_types(id,name,price_minor,currency) VALUES (%s,%s,%s,%s)',
                 (room_id, payload.name, payload.price_minor, payload.currency))
    for day in sorted(set(payload.dates)):
        valid_stay_date(day)
        conn.execute('INSERT INTO room_stock(room_type_id,stay_date,capacity,available) '
                     'VALUES (%s,%s,%s,%s)', (room_id, day, payload.capacity, payload.capacity))
    return {'room_type_id': str(room_id), **payload.model_dump(mode='json')}

# Reserve one unit of inventory for a booking by creating a room hold.
def reserve(conn, booking_id, room_type_id, stay_date):
    valid_stay_date(stay_date)
    # Different Idempotency-Keys still cannot create two holds for one booking.
    conn.lock('hold:' + str(booking_id))
    existing = conn.execute('SELECT * FROM holds WHERE booking_id=%s', (booking_id,)).fetchone()
    if existing:
        if existing['room_type_id'] != str(room_type_id) or existing['stay_date'] != stay_date:
            raise BusinessError(409, 'BOOKING_HOLD_CONFLICT', 'The booking already has a different room hold.')
        return hold_body(existing)
    room = conn.execute('SELECT * FROM room_types WHERE id=%s', (room_type_id,)).fetchone()
    if not room:
        raise BusinessError(404, 'ROOM_TYPE_NOT_FOUND', 'The room type does not exist.')
    # BR2: the database, not an application check-then-update, arbitrates contention.
    updated = conn.execute('UPDATE room_stock SET available=available-1 '
                           'WHERE room_type_id=%s AND stay_date=%s AND available>0',
                           (room_type_id, stay_date))
    require_capacity(updated.rowcount == 1)
    hold_id = uuid4()
    conn.execute('INSERT INTO holds(id,booking_id,room_type_id,stay_date,status,amount_minor,currency) '
                 "VALUES (%s,%s,%s,%s,'HELD',%s,%s)",
                 (hold_id, booking_id, room_type_id, stay_date, room['price_minor'], room['currency']))
    row = conn.execute('SELECT * FROM holds WHERE id=%s', (hold_id,)).fetchone()
    return hold_body(row)

# Convert a database hold record into a JSON-friendly response dictionary.
def hold_body(row):
    return {k: (str(v) if k in {'id','booking_id','room_type_id','stay_date'} else v)
            for k, v in row.items() if k != 'created_at'}


def change_hold(conn, booking_id, action):
    row = conn.execute('SELECT * FROM holds WHERE booking_id=%s FOR UPDATE', (booking_id,)).fetchone()
    if not row:
        raise BusinessError(404, 'HOLD_NOT_FOUND', 'There is no hold for this booking.')
    if action == 'confirm':
        require_confirmable(row['status'])
        conn.execute("UPDATE holds SET status='CONFIRMED' WHERE booking_id=%s", (booking_id,))
    elif row['status'] != 'RELEASED':
        # BR5: release restores capacity once, including a repeated compensation.
        conn.execute('UPDATE room_stock SET available=available+1 WHERE room_type_id=%s AND stay_date=%s',
                     (row['room_type_id'], row['stay_date']))
        conn.execute("UPDATE holds SET status='RELEASED' WHERE booking_id=%s", (booking_id,))
    return hold_body(conn.execute('SELECT * FROM holds WHERE booking_id=%s', (booking_id,)).fetchone())
