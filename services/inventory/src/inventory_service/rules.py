from datetime import date
from .platform import BusinessError


def valid_stay_date(stay_date: date, today: date | None = None):
    """BR1: a one-night booking cannot start in the past."""
    if stay_date < (today or date.today()):
        raise BusinessError(422, 'PAST_STAY_DATE', 'The stay date cannot be in the past.')


def require_capacity(allocated: bool):
    """BR2: allocation must succeed atomically before a hold is created."""
    if not allocated:
        raise BusinessError(409, 'NO_AVAILABILITY', 'No rooms remain for this room type and date.')


def require_confirmable(state: str):
    if state == 'RELEASED':
        raise BusinessError(409, 'HOLD_RELEASED', 'A released hold cannot be confirmed.')
