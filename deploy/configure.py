"""Create a private root .env for Docker. Does not overwrite existing configuration."""
from pathlib import Path
import secrets
ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'.env'
if target.exists(): raise SystemExit('.env already exists; keep it or review it manually.')
keys=['MARIADB_ROOT_PASSWORD']+[n.upper()+'_DB_PASSWORD' for n in ('inventory','reservation','payment','notification')]
target.write_text('# PRIVATE local deployment passwords. Never commit or share.\n'+
                  '\n'.join(key+'='+secrets.token_hex(24) for key in keys)+'\nUI_PORT=8180\n')
try: target.chmod(0o600)
except OSError: pass
print('Created private .env. Passwords were not printed. Keep this file for the retained database volume.')
