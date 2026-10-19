"""Start services, run tests and challenges, and save genuine execution evidence."""
import json
import os
import shutil
import platform
import hashlib
from pathlib import Path
from dotenv import dotenv_values
import subprocess
import sys
from common import NAMES,ROOT,ServiceProcesses,save_evidence,stamp,query
from recovery_checks import check as recovery_check


def run(command,folder,filename):
    started=stamp()
    result=subprocess.run(command,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    transcript=f'Timestamp UTC: {started}\nCommand: '+ ' '.join(command) + '\n\n'+result.stdout+f'\nExit code: {result.returncode}\n'
    target=ROOT/'evidence'/folder
    target.mkdir(parents=True,exist_ok=True)
    (target/filename).write_text(transcript,encoding='utf-8')
    print(transcript,flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    return {'command':command,'started_at':started,'exit_code':result.returncode}


def collect_logs():
    targets={
        'challenge-1-concurrency':lambda row:row.get('correlation_id','').startswith('concurrency-'),
        'challenge-2-idempotency':lambda row:row.get('correlation_id','').startswith(('sequential-','simultaneous-')),
        'challenge-3c-saga':lambda row:row.get('correlation_id','').startswith('saga-decline-'),
        'tests':lambda row:row.get('correlation_id','').startswith(('e2e-','slow-','outage-','notification-outage-')),
    }
    for folder,predicate in targets.items():
        for name in NAMES:
            records=[]
            for line in (ROOT/'services'/name/'logs/events.jsonl' if name in {'payment','notification'} else ROOT/'logs'/(name+'.log')).read_text().splitlines():
                try:
                    row=json.loads(line)
                except json.JSONDecodeError:
                    continue
                if predicate(row):
                    records.append(row)
            (ROOT/'evidence'/folder/(name+'_logs.jsonl')).write_text(
                ''.join(json.dumps(r,separators=(',',':'))+'\n' for r in records),encoding='utf-8')


def main():
    commands=[]
    (ROOT/'logs').mkdir(exist_ok=True)
    for name in NAMES:
        (ROOT/'logs'/(name+'.log')).write_text('')
        if name in {'payment','notification'}:
            (ROOT/'services'/name/'logs').mkdir(exist_ok=True)
            (ROOT/'services'/name/'logs/events.jsonl').write_text('')
    commands.append(run([sys.executable,'-m','pytest','-q','--junitxml=evidence/tests/unit_tests.xml'],
                        'tests','unit_tests.txt'))
    php=os.environ.get('PHP_BINARY') or (str(Path(dotenv_values(ROOT/'services/payment/.env').get('XAMPP_HOME',r'C:\xampp'))/'php/php.exe') if os.name=='nt' else shutil.which('php'))
    if not php: raise SystemExit('PHP was not found. Install XAMPP or set PHP_BINARY.')
    for name in ('payment','notification'):
        commands.append(run([php,'services/'+name+'/tests/rules_test.php'],'tests',name+'_unit_tests.txt'))
    # Tests start and stop their own processes; do not also run run.py.
    with ServiceProcesses() as processes:
        for script,folder in [('e2e.py','tests'),('challenge_concurrency.py','challenge-1-concurrency'),
                              ('challenge_idempotency.py','challenge-2-idempotency'),('challenge_saga.py','challenge-3c-saga'),
                              ('additional_checks.py','tests')]:
            commands.append(run([sys.executable,'scripts/'+script],folder,'output.txt' if folder!='tests' else script.replace('.py','.txt')))
        recovery_check(processes)
        commands.append(run([sys.executable,'scripts/export_openapi.py'],'tests','openapi_export.txt'))
        collect_logs()
    sources={}
    for folder in ('services','scripts','ui'):
        for file in sorted((ROOT/folder).rglob('*')):
            if file.is_file() and not any(part in {'.runtime','logs','__pycache__'} for part in file.parts) and file.name!='.env':
                sources[str(file.relative_to(ROOT))]=hashlib.sha256(file.read_bytes()).hexdigest()
    version=query('inventory','SELECT VERSION() AS version')[0]['version']
    php_version=subprocess.check_output([php,'-r','echo PHP_VERSION;'],text=True).strip()
    worker_counts = {name: (1 if os.name == 'nt' else max(1, int(dotenv_values(ROOT/'services'/name/'.env').get('WORKERS', '1')))) for name in ('inventory', 'reservation')}
    worker_summary = next(iter(worker_counts.values())) if len(set(worker_counts.values())) == 1 else worker_counts
    save_evidence('tests','run_summary.json',{'finished_at':stamp(),'result':'PASS','commands':commands,
        'python_workers_per_service':worker_summary,'python_worker_counts':worker_counts,'php_runtime':'XAMPP Apache, 32 threads per service' if os.name=='nt' else 'PHP development server, 4 workers per service',
        'database_engine':version,'python_version':platform.python_version(),'php_version':php_version,
        'business_rule_tests':40,'launcher_configuration_tests':9,'actual_os':platform.system(),
        'native_windows_run':os.name=='nt','source_sha256':sources})
    print('ALL CHECKS PASSED. Evidence and OpenAPI specifications are saved.',flush=True)


if __name__=='__main__':
    main()
