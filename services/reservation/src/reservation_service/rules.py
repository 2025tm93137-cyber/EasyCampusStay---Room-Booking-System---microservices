from datetime import date
from .platform import BusinessError

TRANSITIONS = {
    'PENDING': {'RESERVED', 'CANCELLED'},
    'RESERVED': {'PAYMENT_PENDING', 'COMPENSATING'},
    'PAYMENT_PENDING': {'PAID', 'PAYMENT_UNCERTAIN', 'COMPENSATING'},
    'PAYMENT_UNCERTAIN': {'PAID', 'COMPENSATING'},
    'PAID': {'CONFIRMED', 'COMPENSATING'},
    'COMPENSATING': {'CANCELLED'},
    'CONFIRMED': set(), 'CANCELLED': set(),
}


def valid_stay_date(stay_date: date, today: date | None = None):
    """BR1: reject past dates before creating any booking."""
    if stay_date < (today or date.today()):
        raise BusinessError(422, 'PAST_STAY_DATE', 'The stay date cannot be in the past.')


def require_transition(current: str, target: str):
    """BR4: only explicit transitions are valid; only PAID can become CONFIRMED."""
    if current != target and target not in TRANSITIONS.get(current, set()):
        raise BusinessError(409, 'INVALID_STATE_TRANSITION', f'Cannot change {current} to {target}.')


def may_release_after_payment(payment_known_successful: bool, refund_completed: bool):
    """BR5: a known successful payment must be refunded before compensation releases its room."""
    if payment_known_successful and not refund_completed:
        raise BusinessError(409, 'REFUND_REQUIRED', 'Refund the successful payment before releasing the room.')
