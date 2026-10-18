from datetime import date, timedelta
import pytest
from inventory_service.platform import BusinessError
from inventory_service.rules import valid_stay_date, require_capacity, require_confirmable


def test_br1_past_date_is_rejected():
    with pytest.raises(BusinessError) as error:
        valid_stay_date(date(2030,1,1),today=date(2030,1,2))
    assert error.value.code=='PAST_STAY_DATE'


@pytest.mark.parametrize('day',[date(2030,1,2),date(2030,1,3)])
def test_br1_today_and_future_dates_are_valid(day):
    valid_stay_date(day,today=date(2030,1,2))


def test_br2_failed_atomic_allocation_is_a_meaningful_conflict():
    with pytest.raises(BusinessError) as error:
        require_capacity(False)
    assert error.value.status==409
    assert error.value.code=='NO_AVAILABILITY'


def test_br2_successful_atomic_allocation_is_allowed():
    require_capacity(True)


def test_released_hold_cannot_be_confirmed():
    with pytest.raises(BusinessError):
        require_confirmable('RELEASED')
