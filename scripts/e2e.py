"""Scripted end-to-end main transaction across all four services."""
from uuid import uuid4
from common import new_room,booking_payload,request,snapshot,save_evidence,stamp


def main():
    started=stamp()
    room,day=new_room(2,'end-to-end')
    cid='e2e-'+str(uuid4())
    payload=booking_payload(room,day,notification_mode='fail_once')
    response=request('reservation','POST','/api/v1/bookings',payload=payload,key=cid,cid=cid)
    assert response.status_code==201,response.text
    assert response.headers['X-Correlation-ID']==cid
    body=response.json()
    assert body['status']=='CONFIRMED' and body['notification_status']=='SENT'
    state=snapshot(room,[body['booking_id']])
    assert state['inventory']['stock'][0]['available']==1
    assert state['inventory']['holds'][0]['status']=='CONFIRMED'
    assert state['payment']['payments'][0]['status']=='CHARGED'
    assert state['notification']['notifications'][0]['attempts']==2
    assert state['notification']['notifications'][0]['status']=='SENT'
    save_evidence('tests','e2e.json',{'started_at':started,'finished_at':stamp(),'correlation_id':cid,
                                  'request':payload,'http_status':response.status_code,'response':body,'database_state':state})
    print('End-to-end | '+started)
    print('PASS: room reserved, mock payment charged, booking confirmed, notification failed once then sent.')


if __name__=='__main__':
    main()
