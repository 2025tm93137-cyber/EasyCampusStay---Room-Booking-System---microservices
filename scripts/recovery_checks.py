"""Supplementary timeout/outage checks. Called by run_all with owned processes."""
import time
from uuid import uuid4
from common import new_room,booking_payload,request,snapshot,save_evidence,stamp


def wait_for_booking(bid,notification='SENT'):
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        response=request('reservation','GET',f'/api/v1/bookings/{bid}')
        if response.json()['status']=='CONFIRMED' and response.json()['notification_status']==notification:
            return response.json()
        time.sleep(0.2)
    raise AssertionError('Booking did not recover within 20 seconds: '+response.text)


def check(processes):
    results=[]
    # The payment mock commits after the HTTP timeout. Recovery reuses its key.
    room,day=new_room(1,'slow-payment')
    payload=booking_payload(room,day,payment_mode='slow_success')
    key='slow-'+str(uuid4())
    first=request('reservation','POST','/api/v1/bookings',payload=payload,key=key,cid=key)
    assert first.status_code==202 and first.json()['status']=='PAYMENT_UNCERTAIN',first.text
    final=wait_for_booking(first.json()['booking_id'])
    replay=request('reservation','POST','/api/v1/bookings',payload=payload,key=key,cid=key)
    assert replay.status_code==202 and replay.json()==first.json()
    state=snapshot(room,[final['booking_id']])
    assert len(state['payment']['payments'])==1 and state['inventory']['stock'][0]['available']==0
    results.append({'scenario':'payment_timeout_after_charge_starts','initial':first.json(),'cached_http_status':202,
                    'final_get':final,'database_state':state})

    # Real stopped process, not a fabricated 503 response.
    processes.stop('payment')
    try:
        room,day=new_room(1,'payment-process-stopped')
        payload=booking_payload(room,day)
        key='outage-'+str(uuid4())
        first=request('reservation','POST','/api/v1/bookings',payload=payload,key=key,cid=key)
        assert first.status_code==202 and first.json()['status']=='PAYMENT_UNCERTAIN',first.text
        held=snapshot(room,[first.json()['booking_id']])
        assert held['inventory']['stock'][0]['available']==0 and not held['payment']['payments']
    finally:
        processes.start('payment')
    final=wait_for_booking(first.json()['booking_id'])
    state=snapshot(room,[final['booking_id']])
    assert len(state['payment']['payments'])==1
    replay=request('reservation','POST','/api/v1/bookings',payload=payload,key=key,cid=key)
    assert replay.status_code==202 and replay.json()==first.json()
    results.append({'scenario':'payment_process_stopped_then_restarted','initial':first.json(),'during_outage':held,
                    'final_get':final,'database_state':state})

    processes.stop('notification')
    try:
        room,day=new_room(1,'notification-process-stopped')
        payload=booking_payload(room,day)
        key='notification-outage-'+str(uuid4())
        first=request('reservation','POST','/api/v1/bookings',payload=payload,key=key,cid=key)
        assert first.status_code==201 and first.json()['status']=='CONFIRMED'
        assert first.json()['notification_status']=='PENDING'
    finally:
        processes.start('notification')
    final=wait_for_booking(first.json()['booking_id'])
    state=snapshot(room,[final['booking_id']])
    assert len(state['notification']['notifications'])==1 and len(state['payment']['payments'])==1
    replay=request('reservation','POST','/api/v1/bookings',payload=payload,key=key,cid=key)
    assert replay.status_code==201 and replay.json()==first.json()
    results.append({'scenario':'notification_process_stopped_then_restarted','initial':first.json(),
                    'final_get':final,'database_state':state})
    save_evidence('tests','recovery_checks.json',{'timestamp':stamp(),'scenarios':results})
    print('PASS: delayed payment and stopped payment recover to one charge; notification outage preserves confirmed booking.')
    print('PASS: original POST status/body stays identical after recovery; GET shows current state.')
