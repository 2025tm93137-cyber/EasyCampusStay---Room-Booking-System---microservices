"""Administrator setup only. No application service imports this script."""
import argparse
from pathlib import Path
import re
import pymysql
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
NAMES=('inventory','reservation','payment','notification')


def schema_statements(name):
    text=(ROOT/'services'/name/'database/schema.sql').read_text(encoding='utf-8')
    text=re.sub(r'^\s*--.*$', '', text, flags=re.M)
    return [statement.strip() for statement in text.split(';') if statement.strip()]


def statements(name, values):
    # Identifiers are generated from a fixed allow-list, never user-supplied SQL.
    db='campusstay_'+name
    grant_db=db.replace('_', '\\_')
    user='cs_'+name
    if values.get('DB_NAME')!=db or values.get('DB_USER')!=user:
        raise SystemExit('Refusing a database/user outside this project naming scheme.')
    esc=pymysql.converters.escape_string
    password=esc(values['DB_PASSWORD'])
    account="'"+user+"'@'127.0.0.1'"
    return [f'CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci',
            f"CREATE USER IF NOT EXISTS {account} IDENTIFIED BY '{password}'",
            f"ALTER USER {account} IDENTIFIED BY '{password}'",
            f'REVOKE ALL PRIVILEGES, GRANT OPTION FROM {account}',
            f'GRANT SELECT,INSERT,UPDATE,DELETE ON `{grant_db}`.* TO {account}',
            f'USE `{db}`',*schema_statements(name)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-sql',action='store_true',help='Write a PRIVATE phpMyAdmin import file instead of connecting')
    args=parser.parse_args()
    configs={name:dotenv_values(ROOT/'services'/name/'.env') for name in NAMES}
    if any(not values.get('DB_PASSWORD') for values in configs.values()):
        raise SystemExit('Run scripts/configure.py first.')
    if args.export_sql:
        target=ROOT/'.runtime/setup_databases.local.sql'
        target.parent.mkdir(exist_ok=True)
        target.write_text('-- PRIVATE: contains application passwords. Do not commit/share.\n'+
                          '\n\n'.join(';\n'.join(statements(name,configs[name]))+';' for name in NAMES)+'\n',encoding='utf-8')
        print('Private import file: .runtime/setup_databases.local.sql. Import locally in phpMyAdmin as the administrator.')
        return
    admin=dotenv_values(ROOT/'.env.admin')
    if not admin.get('ADMIN_USER'): raise SystemExit('Run scripts/configure.py first.')
    connection=pymysql.connect(host=admin['ADMIN_HOST'],port=int(admin['ADMIN_PORT']),user=admin['ADMIN_USER'],
                               password=admin.get('ADMIN_PASSWORD',''),charset='utf8mb4',autocommit=True)
    try:
        with connection.cursor() as cursor:
            version=None
            cursor.execute('SELECT VERSION()');version=cursor.fetchone()[0]
            print('Database engine:',version)
            for name in NAMES:
                user='cs_'+name
                cursor.execute("SELECT Host FROM mysql.user WHERE User=%s AND Host<>'127.0.0.1'",(user,))
                if cursor.fetchone():
                    raise SystemExit(f'Refusing ambiguous {user} accounts on other hosts. Use a dedicated project database installation or review those existing accounts first.')
                cursor.execute("SELECT 1 FROM mysql.user WHERE User=%s AND Host='127.0.0.1'",(user,))
                if cursor.fetchone():
                    cursor.execute("SHOW GRANTS FOR %s@'127.0.0.1'",(user,))
                    for grant in cursor.fetchall():
                        text=grant[0]
                        expected=('campusstay_'+name).replace('_','\\_')
                        own_scope=f'ON `campusstay_{name}`.*' in text or f'ON `{expected}`.*' in text
                        if not text.startswith('GRANT USAGE ON *.*') and not own_scope:
                            raise SystemExit(f'Refusing to reuse {user}: it has permissions outside its project database.')
                for statement in statements(name,configs[name]): cursor.execute(statement)
                print(f'Ready: campusstay_{name}; runtime login {user}; own-database CRUD permissions')
    finally:
        connection.close()


if __name__=='__main__': main()
