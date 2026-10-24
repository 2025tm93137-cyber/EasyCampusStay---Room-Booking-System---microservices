"""Stateless infrastructure, vendored into each independently runnable service."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Callable
from uuid import uuid4

import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .mysql import Connection, json_document
from starlette.exceptions import HTTPException as StarletteHTTPException

# Resolve the service root directory from this module's location.
SERVICE_HOME = Path(__file__).resolve().parents[2]
load_dotenv(SERVICE_HOME / '.env', override=False)
SERVICE_NAME = SERVICE_HOME.name

# Standard structure for an individual API error.
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorResponse(BaseModel):
    error: ErrorDetail

# Document the standard error responses supported by the application.
# These models help describe possible errors in the generated API schema.
ERROR_RESPONSES = {
    status: {'model': ErrorResponse, 'description': description}
    for status, description in {
        400: 'Invalid request', 402: 'Mock payment declined', 404: 'Not found',
        409: 'Business or idempotency conflict', 422: 'Input validation failed',
        503: 'Dependency unavailable', 500: 'Unexpected service error',
    }.items()
}
IdempotencyKey = Annotated[str, Header(alias='Idempotency-Key', min_length=1, max_length=128)]


class BusinessError(Exception):
    def __init__(self, status: int, code: str, message: str, details=None):
        self.status, self.code, self.message, self.details = status, code, message, details
        super().__init__(message)

    def body(self):
        return {'error': {'code': self.code, 'message': self.message, 'details': self.details}}


def log(event: str, correlation_id: str = '', **fields):
    print(json.dumps({
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'service': SERVICE_NAME, 'event': event, 'correlation_id': correlation_id,
        **fields,
    }, default=str, separators=(',', ':')), flush=True)


def database(*, autocommit=False):
    required = ('DB_HOST','DB_PORT','DB_NAME','DB_USER','DB_PASSWORD')
    if not all(key in os.environ for key in required):
        raise RuntimeError('Configure this service .env before starting it.')
    return Connection(dict(os.environ), autocommit=autocommit)


def fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def validate_key(key: str):
    if not key.strip() or key != key.strip() or len(key) > 128:
        raise BusinessError(422, 'INVALID_IDEMPOTENCY_KEY', 'Use a nonblank key of 1 to 128 characters without surrounding spaces.')


def require_same_payload(stored: str, actual: str):
    # BR3: a key identifies one semantic payload, including simulated outcome.
    if stored != actual:
        raise BusinessError(409, 'IDEMPOTENCY_CONFLICT', 'This key was already used with a different request payload.')


def local_idempotent(scope: str, key: str, payload: dict,
                     operation: Callable, correlation_id: str):
    """Lock the request key, commit its effect and response in one local transaction."""
    validate_key(key)
    digest = fingerprint(payload)
    with database() as conn:
        conn.lock('idempotency:' + scope + ':' + key)
        row = conn.execute('SELECT * FROM idempotency_records WHERE scope=%s AND idem_key=%s',
                           (scope, key)).fetchone()
        if row:
            require_same_payload(row['fingerprint'], digest)
            log('idempotency_replay', correlation_id, scope=scope,
                key_hash=hashlib.sha256(key.encode()).hexdigest()[:12])
            return row['http_status'], row['response_body']
        conn.execute('INSERT INTO idempotency_records(scope,idem_key,fingerprint) VALUES (%s,%s,%s)',
                     (scope, key, digest))
        try:
            with conn.transaction():
                status, body = operation(conn)
        except BusinessError as exc:
            status, body = exc.status, exc.body()
        conn.execute('UPDATE idempotency_records SET http_status=%s,response_body=%s '
                     'WHERE scope=%s AND idem_key=%s', (status, json_document(body), scope, key))
    return status, body


def make_app(title: str, *, lifespan=None):
    app = FastAPI(title=title, version='2.0.0', lifespan=lifespan,
                  docs_url=None, redoc_url=None, responses=ERROR_RESPONSES)

    @app.middleware('http')
    async def request_context(request: Request, call_next):
        candidate = request.headers.get('X-Correlation-ID', '')
        cid = candidate if 0 < len(candidate) <= 128 and candidate.isprintable() else str(uuid4())
        request.state.correlation_id = cid
        response = await call_next(request)
        response.headers['X-Correlation-ID'] = cid
        log('http_request', cid, method=request.method, path=request.url.path,
            status=response.status_code)
        return response

    @app.exception_handler(BusinessError)
    async def business_error(request: Request, exc: BusinessError):
        return JSONResponse(status_code=exc.status, content=exc.body())

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        details = [{'location': list(e['loc']), 'message': e['msg'], 'type': e['type']}
                   for e in exc.errors()]
        return JSONResponse(status_code=422, content=BusinessError(
            422, 'VALIDATION_ERROR', 'The request contains invalid fields.', details).body())

    @app.exception_handler(pymysql.Error)
    async def database_error(request: Request, exc: pymysql.Error):
        log('database_error', request.state.correlation_id, exception=type(exc).__name__)
        return JSONResponse(status_code=503, content=BusinessError(
            503, 'DATABASE_UNAVAILABLE', 'The service database is temporarily unavailable.').body())

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content=BusinessError(
            exc.status_code, 'HTTP_ERROR', str(exc.detail)).body(), headers=exc.headers)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        log('unexpected_error', getattr(request.state,'correlation_id',''), exception=type(exc).__name__)
        return JSONResponse(status_code=500, content=BusinessError(
            500, 'INTERNAL_ERROR', 'The service could not complete the request.').body())

    @app.get('/health', tags=['Operations'])
    def health():
        with database() as conn:
            conn.execute('SELECT 1').fetchone()
        return {'status': 'ok', 'service': SERVICE_NAME}

    return app
