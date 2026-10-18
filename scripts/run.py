"""Run the four independent services and optional browser console until Ctrl+C."""
import time
from common import NAMES, ServiceProcesses, base_url


if __name__ == '__main__':
    try:
        with ServiceProcesses(include_ui=True):
            for name in NAMES:
                print(name + ': ' + base_url(name) + ' | /health | /openapi.json', flush=True)
            print('Four services are ready. Browser UI: '+base_url('ui'),flush=True)
            print('Leave this terminal open; Ctrl+C stops the processes owned by this launcher.',flush=True)
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print('Services stopped.')
