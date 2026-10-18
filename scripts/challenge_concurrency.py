"""Challenge 1: at least 20 parallel complete bookings compete for capacity N."""
import argparse
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from common import new_room,booking_payload,request,snapshot,save_evidence,stamp


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--requests',type=int,default=20)
    parser.add_argument('--capacity',type=int,default=5)
    args=parser.parse_args()
    if args.requests<20 or not 0<args.capacity<args.requests:
        parser.error('Use at least 20 requests and 0 < capacity < requests.')
    room,day=new_room(args.capacity,'concurrency')
    barrier=threading.Barrier(args.requests)
    def worker(index):
        payload=booking_payload(room,day,guest_ref=f'parallel-{index}')
        barrier.wait(timeout=20)
        started=stamp()
        response=request('reservation','POST','/api/v1/bookings',payload=payload,key=str(uuid4()),cid=f'concurrency-{room}-{index}')
        return {'request':index,'started_at':started,'http_status':response.status_code,'body':response.json()}
    started=stamp()
    with ThreadPoolExecutor(max_workers=args.requests) as executor:
        results=list(executor.map(worker,range(args.requests)))
    counts=Counter(r['http_status'] for r in results)
    print('Challenge 1 | '+started)
    print(f'Parallel requests={args.requests}, room capacity={args.capacity}, HTTP results={dict(counts)}')
    assert counts=={201:args.capacity,409:args.requests-args.capacity},results
    ids=[]
    for result in results:
        body=result['body']
        if result['http_status']==201:
            assert body['status']=='CONFIRMED'
            ids.append(body['booking_id'])
        else:
            assert body['error']['code']=='NO_AVAILABILITY'
            ids.append(body['error']['details']['booking_id'])
    state=snapshot(room,ids)
    stock=state['inventory']['stock'][0]
    assert stock['available']==0 and stock['capacity']==args.capacity
    assert len(state['inventory']['holds'])==args.capacity
    assert all(h['status']=='CONFIRMED' for h in state['inventory']['holds'])
    assert len(state['payment']['payments'])==args.capacity
    assert all(p['status']=='CHARGED' for p in state['payment']['payments'])
    assert len(state['notification']['notifications'])==args.capacity
    save_evidence('challenge-1-concurrency','results.json',{'started_at':started,'finished_at':stamp(),'requests':args.requests,'capacity':args.capacity,'counts':dict(counts),'responses':results})
    save_evidence('challenge-1-concurrency','database_state.json',state)
    print('PASS: exactly N confirmed; remaining requests rejected; no negative or excess allocation.')


if __name__=='__main__':
    main()
