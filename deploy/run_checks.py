"""Run the original API challenges inside Compose or Kubernetes; no local launchers."""
import json, os, runpy, sys, time
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
NAMES=('inventory','reservation','payment','notification')

def configure():
    for name in NAMES:
        values={'DB_HOST':os.getenv('DB_HOST','db'),'DB_PORT':os.getenv('DB_PORT','3306'),
                'DB_NAME':'campusstay_'+name,'DB_USER':'cs_'+name,
                'DB_PASSWORD':os.environ[name.upper()+'_DB_PASSWORD'],
                'BASE_URL':os.getenv(name.upper()+'_BASE_URL',f'http://{name}:8080')}
        folder=ROOT/'services'/name;folder.mkdir(parents=True,exist_ok=True)
        (folder/'.env').write_text('\n'.join(k+'='+json.dumps(v) for k,v in values.items())+'\n')

def main():
    configure()
    from common import request, query
    summary={'timestamp':datetime.now(timezone.utc).isoformat(),'platform':sys.platform,
             'deployment':os.getenv('DEPLOYMENT_KIND','compose'),'checks':{}}
    failed=False
    for name in NAMES:
        response=request(name,'GET','/health');response.raise_for_status()
        assert response.json().get('service')==name
    # Prove restricted users cannot read another service's schema.
    denied=0
    for own in NAMES:
        for peer in NAMES:
            if own==peer: continue
            table={'inventory':'room_stock','reservation':'bookings','payment':'payments','notification':'notifications'}[peer]
            try: query(own,f'SELECT * FROM campusstay_{peer}.{table} LIMIT 1')
            except Exception as exc:
                if getattr(exc,'args',())[0] not in (1044,1142): raise
                denied+=1
            else: raise AssertionError(f'{own} accessed {peer}')
    summary['peer_database_attempts_denied']=denied
    for script in ('e2e','challenge_concurrency','challenge_idempotency','challenge_saga'):
        start=time.monotonic();sys.argv=[script+'.py']
        try:
            runpy.run_path(str(ROOT/'scripts'/(script+'.py')),run_name='__main__')
            summary['checks'][script]={'result':'PASS','seconds':round(time.monotonic()-start,2)}
        except (Exception,SystemExit) as exc:
            if isinstance(exc,SystemExit) and exc.code in (0,None):
                summary['checks'][script]={'result':'PASS'};continue
            failed=True
            summary['checks'][script]={'result':'FAIL','error':type(exc).__name__}
            print(script,'FAILED; inspect its output',flush=True)
    summary['result']='FAIL' if failed else 'PASS'
    target=ROOT/'evidence'/'assignment2';target.mkdir(parents=True,exist_ok=True)
    (target/'workflow_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2));return int(failed)
if __name__=='__main__': raise SystemExit(main())
