"""Generate four separate application credentials for the local XAMPP database."""
import argparse
import getpass
import json
import os
from pathlib import Path
import secrets

ROOT=Path(__file__).resolve().parents[1]
SERVICES={'inventory':8101,'reservation':8102,'payment':8103,'notification':8104}


def write_env(path, values):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(key+'='+json.dumps(str(value),ensure_ascii=False)+'\n' for key,value in values.items()),encoding='utf-8')
    if os.name!='nt': path.chmod(0o600)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db-host',default='127.0.0.1')
    parser.add_argument('--db-port',type=int,default=3306)
    parser.add_argument('--admin-user',default='root')
    parser.add_argument('--xampp',default=r'C:\xampp')
    parser.add_argument('--force',action='store_true')
    args=parser.parse_args()
    admin=ROOT/'.env.admin'
    if not admin.exists() or args.force:
        password=os.environ.get('CAMPUSSTAY_ADMIN_PASSWORD')
        if password is None:
            password=getpass.getpass('XAMPP database root password (press Enter if your local root password is blank): ')
        write_env(admin,{'ADMIN_HOST':args.db_host,'ADMIN_PORT':args.db_port,'ADMIN_USER':args.admin_user,'ADMIN_PASSWORD':password})
    for name,port in SERVICES.items():
        target=ROOT/'services'/name/'.env'
        if target.exists() and not args.force:
            print(f'Kept services/{name}/.env')
            continue
        values={'DB_HOST':args.db_host,'DB_PORT':args.db_port,'DB_NAME':'campusstay_'+name,
                'DB_USER':'cs_'+name,'DB_PASSWORD':secrets.token_urlsafe(24),
                'HOST':'127.0.0.1','PORT':port,'BASE_URL':f'http://127.0.0.1:{port}',
                'DB_CONNECT_TIMEOUT_SECONDS':5,'WORKERS':2,'XAMPP_HOME':args.xampp}
        if name=='reservation':
            values.update(INVENTORY_URL='http://127.0.0.1:8101',PAYMENT_URL='http://127.0.0.1:8103',
                          NOTIFICATION_URL='http://127.0.0.1:8104',HTTP_TIMEOUT_SECONDS=1.5,
                          IDEMPOTENCY_WAIT_SECONDS=20,RECOVERY_ENABLED='true',RECOVERY_INTERVAL_SECONDS=1)
        if name=='payment': values['PAYMENT_DELAY_SECONDS']=3
        write_env(target,values)
        print(f'Created services/{name}/.env with its own application password')
    ui=ROOT/'ui/.env'
    if not ui.exists() or args.force:
        write_env(ui,{'HOST':'127.0.0.1','PORT':8180,'BASE_URL':'http://127.0.0.1:8180','XAMPP_HOME':args.xampp,
                      **{name.upper()+'_URL':f'http://127.0.0.1:{port}' for name,port in SERVICES.items()}})
    print('Configuration ready. Next run: python scripts/init_databases.py')


if __name__=='__main__': main()
