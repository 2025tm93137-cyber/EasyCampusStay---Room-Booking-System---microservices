"""Developer/test harness. Production services do not import this module."""
import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import httpx
import pymysql
from dotenv import dotenv_values
from db import Connection

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('inventory','reservation','payment','notification')
WINDOWS = os.name == 'nt'


def stop_owned_process(process):
    """Stop this owned Uvicorn parent and its workers, including on Windows."""
    if process.poll() is not None:
        return
    if WINDOWS:
        # Popen.terminate uses TerminateProcess on Windows and can orphan workers.
        # A separate console process group lets Uvicorn handle SIGBREAK gracefully.
        try:
            process.send_signal(getattr(signal, 'CTRL_BREAK_EVENT', 1))
            process.wait(timeout=8)
            return
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        if process.poll() is None:
            taskkill = str(Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'taskkill.exe')
            result = subprocess.run([taskkill, '/PID', str(process.pid), '/T', '/F'],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=10, check=False)
            if result.returncode and process.poll() is None:
                raise RuntimeError('Could not stop an owned service process tree. Check its launcher terminal.')
            process.wait(timeout=3)
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def config(name):
    return dotenv_values((ROOT / 'ui' if name == 'ui' else ROOT / 'services' / name) / '.env')


def base_url(name):
    return os.getenv(name.upper() + '_BASE_URL') or config(name)['BASE_URL']


def request(name, method, path, *, payload=None, key=None, cid=None, timeout=60):
    headers = {'X-Correlation-ID': cid or str(uuid4())}
    if key is not None:
        headers['Idempotency-Key'] = key
    with httpx.Client(timeout=timeout, trust_env=False) as client:
        result = client.request(method, base_url(name) + path, json=payload, headers=headers)
    return result


def new_room(capacity=5, suffix='test', price_minor=250000):
    stay_date = str(date.today() + timedelta(days=7))
    response = request('inventory','POST','/api/v1/room-types', key=str(uuid4()), payload={
        'name': 'Demo ' + suffix + ' ' + str(uuid4())[:8], 'capacity': capacity,
        'price_minor': price_minor, 'currency':'INR', 'dates':[stay_date],
    })
    assert response.status_code == 201, response.text
    return response.json()['room_type_id'], stay_date


def booking_payload(room_type_id, stay_date, **overrides):
    return {'room_type_id':room_type_id,'stay_date':stay_date,'guest_ref':'demo-' + str(uuid4())[:8],
            'recipient':'guest@example.test', 'payment_mode':'success','notification_mode':'success', **overrides}


def query(name, sql_text, params=()):
    # Explicit diagnostic access as each database's own role. These credentials
    # are not inherited by the four service processes.
    with Connection(config(name)) as conn:
        return conn.execute(sql_text, params).fetchall()


def snapshot(room_type_id, booking_ids):
    ids=list(booking_ids)
    placeholders=','.join(['%s']*len(ids)) or 'NULL'
    booking_filter='booking_id IN ('+placeholders+')'
    return {
        'inventory':{
            'stock':query('inventory','SELECT * FROM room_stock WHERE room_type_id=%s',(room_type_id,)),
            'holds':query('inventory','SELECT * FROM holds WHERE room_type_id=%s ORDER BY created_at',(room_type_id,)),
        },
        'reservation':{
            'bookings':query('reservation','SELECT id,status,amount_minor,payment_id,notification_status FROM bookings WHERE room_type_id=%s ORDER BY created_at',(room_type_id,)),
            'steps':query('reservation','SELECT booking_id,from_state,to_state,created_at FROM booking_steps WHERE '+booking_filter+' ORDER BY id',ids),
            'idempotency':query('reservation','SELECT scope,idem_key,fingerprint,booking_id,http_status,response_body FROM idempotency_records WHERE '+booking_filter,ids),
        },
        'payment':{
            'payments':query('payment','SELECT * FROM payments WHERE '+booking_filter+' ORDER BY created_at',ids),
            'refunds':query('payment','SELECT r.* FROM refunds r JOIN payments p ON p.id=r.payment_id WHERE p.'+booking_filter,ids),
        },
        'notification':{'notifications':query('notification','SELECT * FROM notifications WHERE '+booking_filter,ids)},
    }


def save_evidence(folder, name, value):
    target = ROOT / 'evidence' / folder
    target.mkdir(parents=True,exist_ok=True)
    (target / name).write_text(json.dumps(value,indent=2,default=str)+'\n',encoding='utf-8')


def stamp():
    return datetime.now(timezone.utc).isoformat()


class ServiceProcesses:
    def __init__(self, overrides=None, include_ui=False):
        self.processes={}
        self.handles={}
        self.overrides=overrides or {}
        self.names=NAMES + (('ui',) if include_ui else ())

    def start(self,name):
        service_config=config(name)
        with socket.socket() as probe:
            # Probe an actual listener, rather than binding: recently stopped
            # PHP listeners can leave TIME_WAIT sockets on either platform.
            probe.settimeout(0.4)
            if probe.connect_ex((service_config['HOST'],int(service_config['PORT'])))==0:
                raise RuntimeError(f"Port {service_config['PORT']} is already in use. Stop run.py before running tests.")
        (ROOT / 'logs').mkdir(exist_ok=True)
        handle=open(ROOT / 'logs' / (name+'.log'),'a',encoding='utf-8')
        environment=os.environ.copy()
        for secret_key in list(environment):
            if secret_key.startswith(('DB_','ADMIN_','CAMPUSSTAY_ADMIN_')) or secret_key in {'DATABASE_URL','HOTEL_ADMIN_DATABASE_URL'}:
                environment.pop(secret_key,None)
        environment.update({k:v for k,v in service_config.items() if v is not None})
        environment.update(self.overrides.get(name,{}))
        launch_options = {'creationflags': getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x200)} if WINDOWS else {'start_new_session': True}
        try:
            self.processes[name]=subprocess.Popen([sys.executable,str((ROOT/'ui' if name=='ui' else ROOT/'services'/name)/'run.py')],
                                                 cwd=ROOT,env=environment,stdout=handle,stderr=handle,
                                                 **launch_options)
        except BaseException:
            handle.close()
            raise
        self.handles[name]=handle
        self.wait_healthy(name)

    def wait_healthy(self,name):
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            if self.processes[name].poll() is not None:
                raise RuntimeError(f'{name} exited; inspect logs/{name}.log')
            try:
                response=request(name,'GET','/health',timeout=1)
                if response.status_code==200 and response.json().get('service')==name:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        raise RuntimeError(f'{name} did not become healthy; inspect its log')

    def stop(self,name):
        process=self.processes.get(name)
        if process:
            stop_owned_process(process)
            self.processes.pop(name,None)
        handle=self.handles.pop(name,None)
        if handle:
            handle.close()

    def close(self):
        failures=[]
        for name in list(self.processes):
            try:
                self.stop(name)
            except Exception as exc:
                failures.append(f'{name}: {exc}')
        if failures:
            raise RuntimeError('Some owned services did not stop: ' + '; '.join(failures))

    def __enter__(self):
        try:
            for name in self.names:
                self.start(name)
            return self
        except Exception:
            self.close()
            raise

    def __exit__(self,*args):
        self.close()
