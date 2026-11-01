"""One-shot administrative provisioning. Never imported by application services."""
import os, re, time
from pathlib import Path
import pymysql

def main():
    for attempt in range(60):
        try:
            conn=pymysql.connect(host=os.getenv('DB_HOST','db'),port=int(os.getenv('DB_PORT','3306')),user='root',
                                 password=os.environ['MARIADB_ROOT_PASSWORD'],autocommit=True)
            break
        except pymysql.OperationalError:
            if attempt==59: raise
            time.sleep(2)
    try:
        with conn.cursor() as cur:
            for name in ('inventory','reservation','payment','notification'):
                database='campusstay_'+name; user='cs_'+name
                password=os.environ[name.upper()+'_DB_PASSWORD']
                cur.execute(f'CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
                cur.execute("CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s",(user,password))
                cur.execute("ALTER USER %s@'%%' IDENTIFIED BY %s",(user,password))
                cur.execute("REVOKE ALL PRIVILEGES, GRANT OPTION FROM %s@'%%'",(user,))
                # Escape SQL wildcard underscores in database-level GRANT patterns.
                grant_db=database.replace('_',r'\_')
                cur.execute(f"GRANT SELECT,INSERT,UPDATE,DELETE ON `{grant_db}`.* TO %s@'%%'",(user,))
                cur.execute(f'USE `{database}`')
                sql=re.sub(r'^\s*--.*$','',(Path(os.getenv('SCHEMA_DIR',str(Path(__file__).with_name('schemas'))))/(name+'.sql')).read_text(),flags=re.M)
                for statement in sql.split(';'):
                    if statement.strip(): cur.execute(statement)
                print('Provisioned',database,'with a restricted runtime account',flush=True)
    finally: conn.close()
if __name__=='__main__': main()
