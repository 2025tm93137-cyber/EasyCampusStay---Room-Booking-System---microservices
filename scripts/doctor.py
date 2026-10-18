"""Check the beginner setup without printing passwords or administrator settings."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import struct
import subprocess
import sys
import pymysql
from common import ROOT,NAMES,config,base_url,request
from db import Connection


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-stopped',action='store_true')
    parser.add_argument('--apache-check',action='store_true',help='Validate each Windows Apache configuration')
    args=parser.parse_args()
    failed=[]
    print(f'Operating system: {platform.system()} | Python {platform.python_version()} | {struct.calcsize("P")*8}-bit')
    if sys.version_info[:2]!=(3,12) or struct.calcsize('P')*8!=64: failed.append('Use 64-bit Python 3.12 for the bundled wheels.')
    payment=config('payment')
    php=os.environ.get('PHP_BINARY') or (str(Path(payment.get('XAMPP_HOME',r'C:\xampp'))/'php/php.exe') if os.name=='nt' else shutil.which('php'))
    if not php or not Path(php).is_file():
        failed.append('PHP is missing. Check XAMPP_HOME in the generated .env files.')
    else:
        command=[php,'-r',"echo json_encode(['version'=>PHP_VERSION,'pdo_mysql'=>extension_loaded('pdo_mysql'),'curl'=>extension_loaded('curl')]);"]
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            details=json.loads(result.stdout)
            print('PHP:',details['version'],'| PDO MySQL:',details['pdo_mysql'],'| cURL:',details['curl'])
            if tuple(map(int,details['version'].split('.')[:2]))<(8,0) or not details['pdo_mysql'] or not details['curl']:
                failed.append('Use PHP 8.0+ with pdo_mysql and curl enabled in XAMPP php.ini.')
        except (ValueError,KeyError): failed.append('PHP did not start correctly. Run C:\\xampp\\php\\php.exe -v for its error message.')
    for name in NAMES:
        values=config(name)
        if values.get('DB_NAME')!='campusstay_'+name or values.get('DB_USER')!='cs_'+name:
            failed.append(name+': configure the project database and its own application user.');continue
        try:
            with Connection(values) as connection:
                version=connection.execute('SELECT VERSION() AS version').fetchone()['version']
                connection.execute('SELECT COUNT(*) AS n FROM idempotency_records').fetchone()
            print('OK database:',values['DB_NAME'],'| own login |',version)
        except pymysql.Error:
            failed.append(name+': database connection/schema failed; check XAMPP MySQL and run init_databases.py.')
    for name in (*NAMES,'ui'):
        values=config(name)
        if not values.get('PORT'):failed.append(name+': configuration missing.');continue
        with socket.socket() as probe:
            probe.settimeout(0.4)
            occupied=probe.connect_ex((values.get('HOST','127.0.0.1'),int(values['PORT'])))==0
        if occupied and args.require_stopped:failed.append(name+': port '+values['PORT']+' is occupied; stop the prior launcher.')
        print('Port',values['PORT'],name,':','occupied' if occupied else 'free')
    if args.apache_check and os.name=='nt':
        for folder in (ROOT/'services/payment',ROOT/'services/notification',ROOT/'ui'):
            result=subprocess.run([sys.executable,str(folder/'run.py'),'--check'],cwd=ROOT)
            if result.returncode:failed.append(folder.name+': Apache configuration check failed.')
    if failed:
        for item in failed:print('CHECK FAILED:',item)
        raise SystemExit(1)
    print('ENVIRONMENT CHECK PASSED. Start with: python scripts/run.py')


if __name__=='__main__':main()
