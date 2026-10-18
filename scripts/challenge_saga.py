"""Challenge 3C: explicit failure at step 3 undoes the first two steps."""
from uuid import uuid4
from common import new_room,booking_payload,request,snapshot,save_evidence,stamp


def main():
    started=stamp()
    room,day=new_room(1,'saga-compensation')
    payload=booking_payload(room,day,payment_mode='decline')
    key='saga-decline-'+str(uuid4())
    response=request('reservation','POST','/api/v1/bookings',payload=payload,key=key,cid=key)
    assert response.status_code==402,response.text
    bid=response.json()['error']['details']['booking_id']
    state=snapshot(room,[bid])
    save_evidence('challenge-3c-saga','initial_check.json',{'room_type_id':room,'booking_id':bid,'response':response.json(),'database_state':state})
    assert len(state['reservation']['bookings'])==1,state
    assert state['reservation']['bookings'][0]['status']=='CANCELLED'
    assert state['inventory']['stock'][0]['available']==1
    assert state['inventory']['holds'][0]['status']=='RELEASED'
    assert len(state['payment']['payments'])==1 and state['payment']['payments'][0]['status']=='DECLINED'
    assert not state['payment']['refunds'] and not state['notification']['notifications']
    transitions=[s['to_state'] for s in state['reservation']['steps']]
    assert transitions==['PENDING','RESERVED','PAYMENT_PENDING','COMPENSATING','CANCELLED'],transitions
    replay=request('reservation','POST','/api/v1/bookings',payload=payload,key=key,cid=key)
    assert replay.status_code==402 and replay.json()==response.json()
    releases=[]
    for release_key in (bid+':release',bid+':release','alternate-release-'+str(uuid4())):
        released=request('inventory','POST',f'/api/v1/holds/{bid}/release',key=release_key,cid=key)
        assert released.status_code==200 and released.json()['status']=='RELEASED'
        releases.append(released.json())
    state_after_repeats=snapshot(room,[bid])
    assert state_after_repeats['inventory']['stock'][0]['available']==1
    success=request('reservation','POST','/api/v1/bookings',payload=booking_payload(room,day),key=str(uuid4()),cid=key)
    assert success.status_code==201 and success.json()['status']=='CONFIRMED',success.text
    save_evidence('challenge-3c-saga','results.json',{'started_at':started,'finished_at':stamp(),
        'failure_at_step':3,'declined_request':{'http_status':response.status_code,'body':response.json()},
        'transitions':transitions,'repeated_release_results':releases,'subsequent_success':success.json()})
    save_evidence('challenge-3c-saga','database_after_compensation.json',state)
    save_evidence('challenge-3c-saga','database_after_repeated_compensation.json',state_after_repeats)
    print('Challenge 3C | '+started)
    print('Step 3 declined: '+' -> '.join(transitions))
    print('Compensation: room capacity restored to 1, no successful charge, no confirmation.')
    print('PASS: repeated compensation does not over-release; the released room can be booked again.')


if __name__=='__main__':
    main()
