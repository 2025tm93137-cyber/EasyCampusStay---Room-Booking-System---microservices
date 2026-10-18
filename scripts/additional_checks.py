"""Real-database checks for isolation, API errors and business uniqueness."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from uuid import uuid4
import pymysql
from db import Connection
from common import NAMES,config,new_room,booking_payload,request,query,save_evidence,stamp


def main():
    isolation=[]
    for source in NAMES:
        info=config(source)
        with Connection(info) as own:
            assert own.execute('SELECT DATABASE() AS name').fetchone()['name']=='campusstay_'+source
        for target in NAMES:
            if source==target: continue
            denied=False
            try:
                with Connection({**info,'DB_NAME':'campusstay_'+target}): pass
            except pymysql.OperationalError as exc:
                denied=exc.args[0] in {1044,1045}
            assert denied,f'{source} unexpectedly accessed {target}'
            isolation.append({'source':source,'target':target,'result':'DENIED'})
        wrong_password=False
        try:
            with Connection({**info,'DB_PASSWORD':'intentionally-wrong-test-password'}): pass
        except pymysql.OperationalError as exc:
            wrong_password=exc.args[0]==1045
        assert wrong_password,f'{source}: invalid application password was accepted.'
    api_checks=[]
    for name in NAMES:
        spec=request(name,'GET','/openapi.json')
        assert spec.status_code==200 and '/health' in spec.json()['paths']
        missing=request(name,'GET','/missing-path')
        assert missing.status_code==404 and 'error' in missing.json()
        api_checks.append({'service':name,'openapi':'PASS','unknown_path_error':missing.json()})
    invalid=request('reservation','POST','/api/v1/bookings',payload={'room_type_id':'invalid'},key='invalid-'+str(uuid4()))
    assert invalid.status_code==422 and invalid.json()['error']['code']=='VALIDATION_ERROR'
    room,day=new_room(5,'business-uniqueness')
    booking_id=str(uuid4())
    hold_payload={'booking_id':booking_id,'room_type_id':room,'stay_date':day}
    with ThreadPoolExecutor(max_workers=2) as pool:
        holds=list(pool.map(lambda _:request('inventory','POST','/api/v1/holds',payload=hold_payload,key=str(uuid4())),range(2)))
    assert all(h.status_code==201 for h in holds)
    assert holds[0].json()['id']==holds[1].json()['id']
    assert query('inventory','SELECT available FROM room_stock WHERE room_type_id=%s',(room,))[0]['available']==4
    charge={'booking_id':booking_id,'amount_minor':250000,'currency':'INR','simulation':'success'}
    with ThreadPoolExecutor(max_workers=2) as pool:
        payments=list(pool.map(lambda _:request('payment','POST','/api/v1/payments',payload=charge,key=str(uuid4())),range(2)))
    assert all(p.status_code==201 for p in payments)
    assert payments[0].json()['id']==payments[1].json()['id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        refunds=list(pool.map(lambda _:request('payment','POST',f'/api/v1/payments/{booking_id}/refund',key=str(uuid4())),range(2)))
    assert all(r.status_code==200 and r.json()['status']=='REFUNDED' for r in refunds)
    refund_rows=query('payment','SELECT r.id,r.amount_minor FROM refunds r JOIN payments p ON r.payment_id=p.id WHERE p.booking_id=%s',(booking_id,))
    assert len(refund_rows)==1
    past_payload=booking_payload(room,str(date.today()-timedelta(days=1)))
    past=request('reservation','POST','/api/v1/bookings',payload=past_payload,key=str(uuid4()))
    assert past.status_code==422 and past.json()['error']['code']=='PAST_STAY_DATE'
    assert not query('reservation','SELECT id FROM bookings WHERE room_type_id=%s',(room,))
    save_evidence('tests','additional_checks.json',{'timestamp':stamp(),'database_isolation':isolation,
        'api_checks':api_checks,'invalid_request':invalid.json(),'different_keys_same_booking':{
            'hold_id':holds[0].json()['id'],'payment_id':payments[0].json()['id'],'refund_records':refund_rows},
        'past_date_request':past.json()})
    print('PASS: all 12 cross-database connections denied; four OpenAPI specs and consistent error responses.')
    print('PASS: different keys cannot duplicate a hold, payment or refund; invalid past date creates no booking.')


if __name__=='__main__':
    main()
