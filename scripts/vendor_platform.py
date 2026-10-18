"""Synchronise stateless infrastructure copies, never service business rules."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    for name in ('inventory','reservation'):
        (ROOT/'services'/name/'src'/(name+'_service')/'mysql.py').write_text((ROOT/'tools/templates/mysql.py').read_text())
    (ROOT/'scripts/db.py').write_text((ROOT/'tools/templates/mysql.py').read_text())
    for name in ('payment','notification'):
        (ROOT/'services'/name/'src/platform.php').write_text((ROOT/'tools/templates/platform.php').read_text())
    for folder in [ROOT/'services/payment',ROOT/'services/notification',ROOT/'ui']:
        (folder/'run.py').write_text((ROOT/'tools/templates/php_runtime.py').read_text())
        (folder/'public/router.php').write_text((ROOT/'tools/templates/router.php').read_text())
    print('Infrastructure copies synchronised.')
