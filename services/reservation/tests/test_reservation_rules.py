from datetime import date
import pytest
from reservation_service.platform import BusinessError, fingerprint, require_same_payload, validate_key
from reservation_service.rules import require_transition, may_release_after_payment, valid_stay_date
from reservation_service.main import BookingCreate


def test_br1_reservation_rejects_past_date():
    with pytest.raises(BusinessError):
        valid_stay_date(date(2030,1,1),today=date(2030,1,2))


def test_br3_semantic_json_fingerprint_ignores_field_order():
    assert fingerprint({'a':1,'b':2})==fingerprint({'b':2,'a':1})


def test_br3_same_key_with_changed_payload_is_rejected():
    with pytest.raises(BusinessError) as error:
        require_same_payload(fingerprint({'amount':1}),fingerprint({'amount':2}))
    assert error.value.status==409


def test_br3_same_key_with_identical_payload_is_allowed():
    require_same_payload(fingerprint({'amount':1}),fingerprint({'amount':1}))


@pytest.mark.parametrize('key',['',' ',' leading','trailing ','x'*129])
def test_br3_invalid_key_is_rejected(key):
    with pytest.raises(BusinessError):
        validate_key(key)


def test_br3_default_values_have_the_same_semantic_fingerprint():
    raw={'room_type_id':'12345678-1234-1234-1234-123456789abc','stay_date':'2030-01-02','guest_ref':'guest'}
    first=BookingCreate(**raw).model_dump(mode='json')
    explicit=BookingCreate(**first).model_dump(mode='json')
    assert fingerprint(first)==fingerprint(explicit)


@pytest.mark.parametrize('state',['PENDING','RESERVED','PAYMENT_PENDING','PAYMENT_UNCERTAIN','COMPENSATING','CANCELLED'])
def test_br4_unpaid_or_cancelled_booking_cannot_be_confirmed(state):
    with pytest.raises(BusinessError):
        require_transition(state,'CONFIRMED')


def test_br4_paid_booking_can_be_confirmed():
    require_transition('PAID','CONFIRMED')


def test_br5_successful_payment_requires_refund_before_release():
    with pytest.raises(BusinessError) as error:
        may_release_after_payment(True,False)
    assert error.value.code=='REFUND_REQUIRED'


@pytest.mark.parametrize('paid,refunded',[(False,False),(True,True)])
def test_br5_declined_or_refunded_payment_allows_compensation(paid,refunded):
    may_release_after_payment(paid,refunded)
