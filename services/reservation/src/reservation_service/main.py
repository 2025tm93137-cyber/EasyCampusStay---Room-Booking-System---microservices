"""Mujaffars Reservation code main file."""
import hashlib
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import date
from typing import Literal
from uuid import UUID
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from .platform import IdempotencyKey, log, make_app
from . import repository, saga
from .rules import valid_stay_date


def recovery_loop(stop):
    interval = float(os.getenv('RECOVERY_INTERVAL_SECONDS','1'))
    while not stop.wait(interval):
        try:
            for row in repository.recovery_candidates():
                if stop.is_set():
                    return
                saga.run(row['id'], row['correlation_id'])
        except Exception as exc:
            log('recovery_error', reason=type(exc).__name__)


@asynccontextmanager
async def lifespan(app):
    stop = threading.Event()
    thread = None
    if os.getenv('RECOVERY_ENABLED','true').lower() == 'true':
        thread = threading.Thread(target=recovery_loop, args=(stop,), daemon=True, name='booking-recovery')
        thread.start()
    yield
    stop.set()
    if thread:
        thread.join(timeout=3)


app = make_app('CampusStay Reservation Service', lifespan=lifespan)


class BookingCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    room_type_id: UUID
    stay_date: date
    guest_ref: str = Field(min_length=1, max_length=80)
    recipient: str = Field(default='guest@example.test', min_length=1, max_length=254)
    payment_mode: Literal['success','decline','slow_success'] = 'success'
    notification_mode: Literal['success','fail_once'] = 'success'


class BookingResponse(BaseModel):
    booking_id: UUID
    status: Literal['PENDING','RESERVED','PAYMENT_PENDING','PAYMENT_UNCERTAIN','PAID','CONFIRMED','COMPENSATING','CANCELLED']
    room_type_id: UUID
    stay_date: date
    amount_minor: int | None
    currency: str | None
    payment_id: UUID | None
    notification_status: Literal['PENDING','SENT']


@app.post('/api/v1/bookings', status_code=201, response_model=BookingResponse,
          responses={202: {'model': BookingResponse, 'description': 'Accepted; GET the booking to observe recovery'}},
          tags=['Bookings'])
def book(payload: BookingCreate, key: IdempotencyKey, request: Request):
    cid = request.state.correlation_id
    booking_id, cached = repository.claim(key, payload.model_dump(mode='json'), cid)
    if cached:
        log('idempotency_replay', cid, booking_id=str(booking_id), key_hash=hashlib.sha256(key.encode()).hexdigest()[:12])
        return JSONResponse(status_code=cached[0], content=cached[1])
    deadline = time.monotonic() + float(os.getenv('IDEMPOTENCY_WAIT_SECONDS','20'))
    while time.monotonic() < deadline:
        result = saga.run(booking_id, cid)
        if result is not None:
            # If another worker cached an acceptance, preserve that same response.
            result = repository.cached_response(booking_id) or result
            return JSONResponse(status_code=result[0], content=result[1])
        cached = repository.cached_response(booking_id)
        if cached:
            log('idempotency_replay', cid, booking_id=str(booking_id), concurrent=True)
            return JSONResponse(status_code=cached[0], content=cached[1])
        time.sleep(0.05)
    # Rare owner still running: commit one immutable acceptance snapshot.
    result = saga.pending(booking_id)
    repository.cache_response(booking_id, *result)
    cached = repository.cached_response(booking_id)
    return JSONResponse(status_code=cached[0], content=cached[1])


@app.get('/api/v1/bookings/{booking_id}', response_model=BookingResponse, tags=['Bookings'])
def booking(booking_id: UUID):
    return repository.response_body(repository.read(booking_id))


@app.get('/api/v1/bookings/{booking_id}/steps', tags=['Bookings'])
def steps(booking_id: UUID):
    repository.read(booking_id)
    return {'booking_id': str(booking_id), 'steps': repository.steps(booking_id)}


@app.post('/api/v1/bookings/{booking_id}/recover', response_model=BookingResponse,
          tags=['Recovery'])
def recover(booking_id: UUID, request: Request):
    repository.read(booking_id)
    saga.run(booking_id, request.state.correlation_id)
    # This command advances the same workflow; it never creates a second booking.
    return repository.response_body(repository.read(booking_id))
