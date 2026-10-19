"""Independently launch this service from its own folder."""
import os
from pathlib import Path
from dotenv import load_dotenv
import uvicorn

if __name__ == '__main__':
    folder=Path(__file__).resolve().parent
    load_dotenv(folder/'.env',override=False)
    if not os.getenv('DB_NAME'):
        raise SystemExit('Set DB_NAME or create .env from .env.example first.')
    requested_workers = max(1, int(os.getenv('WORKERS', '1')))
    # Some Windows installations fail while sharing listening sockets between
    # spawned workers (WinError 10022). Local assignment mode avoids that path.
    workers = 1 if os.name == 'nt' else requested_workers
    if workers != requested_workers:
        print('Windows local mode: using 1 Python worker to avoid shared-socket startup failures.', flush=True)
    uvicorn.run(folder.name+'_service.main:app',app_dir=str(folder/'src'),
                host=os.environ['HOST'],port=int(os.environ['PORT']),
                workers=workers,access_log=False)
