# CampusStay Inventory service

Language: Python / FastAPI. Database: `campusstay_inventory`. Runtime login: `cs_inventory`.

API entry, business rules and database operations: `src/inventory_service/main.py`, `src/inventory_service/rules.py`, `src/inventory_service/repository.py`.

`database/schema.sql` contains only this service's tables. The database creation SQL and user template are in the same folder. Provision schema as administrator; runtime permissions are own-database CRUD.

After project setup, run from the root in its own PowerShell terminal:

```powershell
.\.venv\Scripts\python.exe services\inventory\run.py
```

The launcher reads this folder's `.env`. Dependencies are declared in requirements.lock.txt. Configuration examples are in `.env.example`.

Read the root README and [beginner guide](../../docs/BEGINNER_WINDOWS_GUIDE.md) for software, SQL, testing and video steps.
