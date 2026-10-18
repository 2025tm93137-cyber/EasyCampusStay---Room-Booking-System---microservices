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
    uvicorn.run(folder.name+'_service.main:app',app_dir=str(folder/'src'),
                host=os.environ['HOST'],port=int(os.environ['PORT']),
                workers=int(os.getenv('WORKERS','1')),access_log=False)
