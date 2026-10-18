"""Standalone PHP runtime launcher. Windows uses XAMPP Apache with its own config.

Each launcher owns its process tree; it does not edit XAMPP's global httpd.conf.
Linux verification uses PHP's multi-worker development server.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys

SERVICE_DIR=Path(__file__).resolve().parent


def environment():
    values={}
    file=SERVICE_DIR/'.env'
    if file.exists():
        for line in file.read_text(encoding='utf-8').splitlines():
            if not line.strip() or line.lstrip().startswith('#') or '=' not in line: continue
            key,value=line.split('=',1)
            value=value.strip()
            values[key.strip()]=str(json.loads(value)) if value.startswith('"') else value
    values.update(os.environ)
    return values


def apache_configuration(folder, xampp, host, port, static_modules):
    """Build one local server configuration, with PHP and a public-only document root."""
    server=xampp/'apache'
    runtime=folder/'.runtime/apache'
    runtime.mkdir(parents=True,exist_ok=True)
    quoted=lambda path:'"'+Path(path).resolve().as_posix()+'"'
    lines=['ServerRoot '+quoted(server),f'Listen {host}:{port}',f'ServerName {host}:{port}',
           'PidFile '+quoted(runtime/'httpd.pid'),'ErrorLog '+quoted(runtime/'error.log'),'LogLevel warn']
    modules=['authz_core','authz_host','dir','mime','log_config']
    for module in modules:
        if ('mod_'+module+'.c') in static_modules: continue
        path=server/'modules'/('mod_'+module+'.so')
        if not path.is_file(): raise RuntimeError('Missing XAMPP Apache module: '+str(path))
        lines.append('LoadModule '+module+'_module '+quoted(path))
    php=xampp/'php'
    for path in (php/'php8ts.dll',php/'php8apache2_4.dll'):
        if not path.is_file(): raise RuntimeError('Use an XAMPP package with thread-safe PHP 8.0 or later: '+str(path))
    lines+=['LoadFile '+quoted(php/'php8ts.dll'),'LoadModule php_module '+quoted(php/'php8apache2_4.dll'),
            'PHPIniDir '+quoted(php),'TypesConfig '+quoted(server/'conf/mime.types'),
            'DocumentRoot '+quoted(folder/'public'),'<Directory '+quoted(folder/'public')+'>',
            '  Require local','  AllowOverride None','  Options -Indexes','  DirectoryIndex index.php',
            '  FallbackResource /index.php','</Directory>',
            '<FilesMatch "\\.php$">','  SetHandler application/x-httpd-php','</FilesMatch>',
            '<IfModule mpm_winnt_module>','  ThreadsPerChild 32','  MaxConnectionsPerChild 0','</IfModule>']
    target=runtime/'httpd.conf'
    target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return target


def stop_child(process):
    if process.poll() is not None: return
    if os.name=='nt':
        # Signals delivered to this console group normally stop Apache first.
        # If it remains, stop only the explicitly owned Apache process tree.
        try: process.wait(timeout=2);return
        except subprocess.TimeoutExpired: pass
        taskkill=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/taskkill.exe'
        subprocess.run([str(taskkill),'/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        process.wait(timeout=8)
    else:
        try: os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError: return
        try: process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)


def interrupted(*args): raise KeyboardInterrupt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xampp',help='XAMPP installation folder, normally C:\\xampp')
    parser.add_argument('--check',action='store_true',help='Validate Apache config without starting the service')
    args=parser.parse_args()
    values=environment()
    host=values.get('HOST','127.0.0.1')
    port=int(values.get('PORT','8180' if SERVICE_DIR.name=='ui' else '8103'))
    if host not in {'127.0.0.1','localhost'}: raise SystemExit('This local assignment launcher binds to loopback. Use a separate deployment config for hosting.')
    for event in ('SIGTERM','SIGBREAK'):
        if hasattr(signal,event): signal.signal(getattr(signal,event),interrupted)
    if os.name=='nt':
        xampp=Path(args.xampp or values.get('XAMPP_HOME',r'C:\xampp'))
        httpd=xampp/'apache/bin/httpd.exe'
        if not httpd.is_file(): raise SystemExit('XAMPP Apache was not found. Check XAMPP_HOME in this service .env.')
        values['PATH']=str(xampp/'php')+os.pathsep+values.get('PATH','')
        static=subprocess.check_output([str(httpd),'-l'],env=values,text=True,stderr=subprocess.STDOUT)
        conf=apache_configuration(SERVICE_DIR,xampp,host,port,static)
        subprocess.run([str(httpd),'-t','-f',str(conf)],env=values,check=True)
        if args.check: return
        command=[str(httpd),'-f',str(conf),'-DFOREGROUND']
        options={}
        label='XAMPP Apache / PHP'
    else:
        php=values.get('PHP_BINARY') or shutil.which('php')
        if not php: raise SystemExit('PHP is missing; set PHP_BINARY to its executable.')
        if args.check:
            subprocess.run([php,'-l',str(SERVICE_DIR/'public/index.php')],check=True,env=values);return
        values['PHP_CLI_SERVER_WORKERS']=values.get('PHP_CLI_SERVER_WORKERS','4')
        command=[php,'-S',f'{host}:{port}','-t',str(SERVICE_DIR/'public'),str(SERVICE_DIR/'public/router.php')]
        options={'start_new_session':True}
        label='PHP multi-worker development server (Linux verification)'
    print(f'{SERVICE_DIR.name}: {label} | http://{host}:{port}',flush=True)
    child=subprocess.Popen(command,cwd=SERVICE_DIR,env=values,**options)
    try:
        code=child.wait()
        if code: raise SystemExit(code)
    except KeyboardInterrupt: pass
    finally: stop_child(child)


if __name__=='__main__': main()
