"""Challenge 2: sequential replay, simultaneous first requests and changed payload."""
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from common import new_room,booking_payload,request,snapshot,save_evidence,stamp


def assert_one(state):
    assert len(state['reservation']['bookings'])==1
    assert len(state['reservation']['idempotency'])==1
    assert len(state['inventory']['holds'])==1
    assert len(state['payment']['payments'])==1
    assert len(state['notification']['notifications'])==1
    assert state['inventory']['stock'][0]['available']==4


def main():
    started=stamp()
    room,day=new_room(5,'sequential-idempotency')
    payload=booking_payload(room,day)
    key='sequential-'+str(uuid4())
    first=request('reservation','POST','/api/v1/bookings',payload=payload,key=key,cid=key)
    assert first.status_code==201,first.text
    repeats=[]
    for _ in range(3):
        response=request('reservation','POST','/api/v1/bookings',payload=payload,key=key,cid=key)
        assert response.status_code==first.status_code and response.json()==first.json()
        repeats.append({'http_status':response.status_code,'body':response.json()})
    conflict=request('reservation','POST','/api/v1/bookings',payload={**payload,'guest_ref':'changed-payload'},key=key,cid=key)
    assert conflict.status_code==409 and conflict.json()['error']['code']=='IDEMPOTENCY_CONFLICT'
    sequential_state=snapshot(room,[first.json()['booking_id']])
    assert_one(sequential_state)

    room2,day2=new_room(5,'concurrent-idempotency')
    payload2=booking_payload(room2,day2)
    key2='simultaneous-'+str(uuid4())
    barrier=threading.Barrier(20)
    def worker(index):
        barrier.wait(timeout=20)
        result=request('reservation','POST','/api/v1/bookings',payload=payload2,key=key2,cid=key2)
        return {'request':index,'http_status':result.status_code,'body':result.json()}
    with ThreadPoolExecutor(max_workers=20) as executor:
        results=list(executor.map(worker,range(20)))
    assert all(r['http_status']==201 and r['body']==results[0]['body'] for r in results),results
    simultaneous_state=snapshot(room2,[results[0]['body']['booking_id']])
    assert_one(simultaneous_state)
    save_evidence('challenge-2-idempotency','results.json',{'started_at':started,'finished_at':stamp(),
        'first_call':{'http_status':first.status_code,'body':first.json()},'sequential_replays':repeats,
        'payload_conflict':{'http_status':conflict.status_code,'body':conflict.json()},'simultaneous_first_calls':results,
        'correlation_ids':[key,key2]})
    save_evidence('challenge-2-idempotency','database_state.json',{'sequential':sequential_state,'simultaneous':simultaneous_state})
    print('Challenge 2 | '+started)
    print('Sequential: first + 3 replays are identical; changed payload returns 409.')
    print('Concurrent: 20 identical first requests return the same booking and HTTP 201.')
    print('PASS: one booking, one hold, one charge and one notification per key.')


if __name__=='__main__':
    main()
