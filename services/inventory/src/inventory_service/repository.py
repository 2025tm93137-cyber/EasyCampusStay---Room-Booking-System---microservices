
"""
Repository functions for the CampusStay Inventory Service.

This module handles database operations related to room types,
room availability, reservations, and booking holds.
"""

from uuid import uuid4

from .platform import BusinessError
from .rules import require_capacity, require_confirmable, valid_stay_date


def create_room_type(conn, payload):
    """
    Create a new room type and initialize its available room stock.

    A stock record is created for each unique stay date provided
    in the room type request.
    """

    # Generate a unique identifier for the new room type.
    room_id = uuid4()

    # Store the room type details in the database.
    conn.execute('INSERT INTO room_types(id,name,price_minor,currency) VALUES (%s,%s,%s,%s)',
                 (room_id, payload.name, payload.price_minor, payload.currency))

    # Initialize room capacity for each unique stay date.
    for day in sorted(set(payload.dates)):
        valid_stay_date(day)

        conn.execute('INSERT INTO room_stock(room_type_id,stay_date,capacity,available) '
                     'VALUES (%s,%s,%s,%s)', (room_id, day, payload.capacity, payload.capacity))

    # Return the newly created room type details.
    return {'room_type_id': str(room_id), **payload.model_dump(mode='json')}


def reserve(conn, booking_id, room_type_id, stay_date):
    """
    Reserve one room for a booking on the requested stay date.

    Checks for an existing hold, validates the room type,
    and decreases available stock before creating a new hold.
    """

    # Ensure that the requested stay date is valid.
    valid_stay_date(stay_date)

    # Different Idempotency-Keys still cannot create two holds for one booking.
    conn.lock('hold:' + str(booking_id))

    # Check whether this booking already has a room hold.
    existing = conn.execute('SELECT * FROM holds WHERE booking_id=%s', (booking_id,)).fetchone()

    if existing:
        # Reject attempts to reserve a different room or date for the same booking.
        if existing['room_type_id'] != str(room_type_id) or existing['stay_date'] != stay_date:
            raise BusinessError(409, 'BOOKING_HOLD_CONFLICT', 'The booking already has a different room hold.')

        # Return the existing hold if the reservation details match.
        return hold_body(existing)

    # Verify that the requested room type exists.
    room = conn.execute('SELECT * FROM room_types WHERE id=%s', (room_type_id,)).fetchone()

    if not room:
        raise BusinessError(404, 'ROOM_TYPE_NOT_FOUND', 'The room type does not exist.')

    # BR2: the database, not an application check-then-update, arbitrates contention.
    # Decrease availability only when at least one room is still available.
    updated = conn.execute('UPDATE room_stock SET available=available-1 '
                           'WHERE room_type_id=%s AND stay_date=%s AND available>0',
                           (room_type_id, stay_date))

    # Ensure that the stock update was successful before creating the hold.
    require_capacity(updated.rowcount == 1)

    # Generate a unique identifier for the reservation hold.
    hold_id = uuid4()

    # Insert the new hold with its initial HELD status and room price.
    conn.execute('INSERT INTO holds(id,booking_id,room_type_id,stay_date,status,amount_minor,currency) '
                 "VALUES (%s,%s,%s,%s,'HELD',%s,%s)",
                 (hold_id, booking_id, room_type_id, stay_date, room['price_minor'], room['currency']))

    # Retrieve and return the newly created hold.
    row = conn.execute('SELECT * FROM holds WHERE id=%s', (hold_id,)).fetchone()

    return hold_body(row)


def hold_body(row):
    """
    Convert a database hold record into an API-friendly dictionary.

    Converts identifier and date fields to strings and excludes
    the internal created_at field from the response.
    """

    return {k: (str(v) if k in {'id','booking_id','room_type_id','stay_date'} else v)
            for k, v in row.items() if k != 'created_at'}


def change_hold(conn, booking_id, action):
    """
    Confirm or release an existing booking hold.

    Uses a database row lock to protect the hold while its status
    and corresponding room availability are updated.
    """

    # Retrieve and lock the hold associated with the booking.
    row = conn.execute('SELECT * FROM holds WHERE booking_id=%s FOR UPDATE', (booking_id,)).fetchone()

    if not row:
        raise BusinessError(404, 'HOLD_NOT_FOUND', 'There is no hold for this booking.')

    # Confirm the hold if the requested action is confirmation.
    if action == 'confirm':
        require_confirmable(row['status'])

        conn.execute("UPDATE holds SET status='CONFIRMED' WHERE booking_id=%s", (booking_id,))

    # Release the hold and restore room availability when applicable.
    elif row['status'] != 'RELEASED':

        # BR5: release restores capacity once, including a repeated compensation.
        conn.execute('UPDATE room_stock SET available=available+1 WHERE room_type_id=%s AND stay_date=%s',
                     (row['room_type_id'], row['stay_date']))

        conn.execute("UPDATE holds SET status='RELEASED' WHERE booking_id=%s", (booking_id,))

    # Return the latest hold details after the requested operation.
    return hold_body(conn.execute('SELECT * FROM holds WHERE booking_id=%s', (booking_id,)).fetchone())
