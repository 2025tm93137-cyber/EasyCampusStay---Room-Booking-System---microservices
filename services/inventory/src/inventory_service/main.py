
"""
Main API module for the CampusStay Inventory Service.

This module defines request and response models and exposes REST APIs
for room type management, availability checking, and reservation holds.
"""

from datetime import date
from uuid import UUID
from typing import Literal

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .platform import (
    BusinessError,
    IdempotencyKey,
    database,
    local_idempotent,
    make_app
)
from . import repository


# Initialize the FastAPI application for the Inventory Service.
app = make_app('CampusStay Inventory Service')

# Defines the validation rules for creating a room type.
# Extra fields are rejected to prevent unexpected input.
# Capacity, price, currency, and dates are validated before
# the request reaches the database layer.
class RoomTypeCreate(BaseModel):
    """Validates the details required to create a new room type."""

    model_config = ConfigDict(extra='forbid')

    name: str = Field(min_length=1, max_length=80)
    capacity: int = Field(ge=1, le=1000)
    price_minor: int = Field(gt=0)
    currency: str = Field(default='INR', pattern=r'^[A-Z]{3}$')
    dates: list[date] = Field(min_length=1, max_length=60)


class HoldCreate(BaseModel):
    """Defines the room and booking details required for a reservation hold."""

    model_config = ConfigDict(extra='forbid')

    booking_id: UUID
    room_type_id: UUID
    stay_date: date


class RoomTypeResponse(RoomTypeCreate):
    """Represents the room type details returned after creation."""

    room_type_id: UUID


class AvailabilityResponse(BaseModel):
    """Represents room capacity and remaining availability for a date."""

    room_type_id: UUID
    stay_date: date
    capacity: int
    available: int


class HoldResponse(BaseModel):
    """Represents the current status and details of a reservation hold."""

    id: UUID
    booking_id: UUID
    room_type_id: UUID
    stay_date: date
    status: Literal['HELD', 'CONFIRMED', 'RELEASED']
    amount_minor: int
    currency: str


# -------------------- Room Inventory APIs --------------------

@app.get('/api/v1/room-types', tags=['Room inventory'])
def list_room_types():
    """Retrieve the available room types from the inventory database."""

    with database() as conn:
        rows = conn.execute(
            'SELECT id AS room_type_id,name,price_minor,currency '
            'FROM room_types ORDER BY name,id LIMIT 100'
        ).fetchall()

    return {'room_types': rows}


@app.post('/api/v1/room-types', status_code=201, response_model=RoomTypeResponse, tags=['Room inventory'])
def create_room_type(payload: RoomTypeCreate, key: IdempotencyKey, request: Request):
    # Reuse the result of a previous request with the same
    # idempotency key to avoid duplicate room type creation.
    def create(conn):
        return 201, repository.create_room_type(conn, payload)

    # Use an idempotency key to prevent duplicate room type creation
    # when the same request is submitted multiple times.
    status, body = local_idempotent(
        'room-types:create',
        key,
        payload.model_dump(mode='json'),
        create,
        request.state.correlation_id
    )

    return JSONResponse(status_code=status, content=body)


@app.get(
    '/api/v1/room-types/{room_type_id}/availability',
    response_model=AvailabilityResponse,
    tags=['Room inventory']
)
def availability(room_type_id: UUID, stay_date: date):
    """Check the total and remaining room availability for a specific date."""

    with database() as conn:
        row = conn.execute(
            'SELECT room_type_id,stay_date,capacity,available FROM room_stock '
            'WHERE room_type_id=%s AND stay_date=%s',
            (room_type_id, stay_date)
        ).fetchone()

    # Return a not-found error if inventory has not been initialized.
    if not row:
        raise BusinessError(
            404,
            'AVAILABILITY_NOT_FOUND',
            'There is no inventory for this date.'
        )

    return {
        **row,
        'room_type_id': str(row['room_type_id']),
        'stay_date': str(row['stay_date'])
    }


# -------------------- Reservation Hold APIs --------------------

@app.post(
    '/api/v1/holds',
    status_code=201,
    response_model=HoldResponse,
    tags=['Room holds']
)
def reserve(payload: HoldCreate, key: IdempotencyKey, request: Request):
    # Create a room hold through the repository layer.
    # Idempotency prevents duplicate holds when the same request is retried.
    status, body = local_idempotent('holds:create', key, payload.model_dump(mode='json'),
                                  lambda conn: (201, repository.reserve(conn, **payload.model_dump())),
                                  request.state.correlation_id)
    return JSONResponse(status_code=status, content=body)


@app.get('/api/v1/holds/{booking_id}', response_model=HoldResponse, tags=['Room holds'])
def get_hold(booking_id: UUID):
    """Retrieve the reservation hold associated with a booking ID."""

    with database() as conn:
        row = conn.execute(
            'SELECT * FROM holds WHERE booking_id=%s',
            (booking_id,)
        ).fetchone()

    if not row:
        raise BusinessError(
            404,
            'HOLD_NOT_FOUND',
            'There is no hold for this booking.'
        )

    return repository.hold_body(row)


@app.post(
    '/api/v1/holds/{booking_id}/confirm',
    response_model=HoldResponse,
    tags=['Room holds']
)
def confirm(booking_id: UUID, key: IdempotencyKey, request: Request):
    """Confirm an existing reservation hold for the specified booking."""

    return change_hold(booking_id, 'confirm', key, request)


@app.post(
    '/api/v1/holds/{booking_id}/release',
    response_model=HoldResponse,
    tags=['Room holds']
)
def release(booking_id: UUID, key: IdempotencyKey, request: Request):
    """Release a reservation hold and restore the associated room availability."""

    return change_hold(booking_id, 'release', key, request)


# -------------------- Shared Hold Management --------------------

def change_hold(booking_id, action, key, request):
    # Confirm or release an existing hold through the repository.
    # The idempotency key helps make retries safe.
    status, body = local_idempotent('holds:' + action, key, {'booking_id': str(booking_id)},
                                  lambda conn: (200, repository.change_hold(conn, booking_id, action)),
                                  request.state.correlation_id)
    return JSONResponse(status_code=status, content=body)
