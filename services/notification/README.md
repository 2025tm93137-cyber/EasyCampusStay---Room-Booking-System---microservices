# CampusStay Notification service

Language: PHP / PDO MySQL. Database: `campusstay_notification`. Runtime login: `cs_notification`.

API entry, business rules and database operations: `src/main.php`, `src/rules.php`, `src/repository.php`.

`database/schema.sql` contains only this service's tables. The database creation SQL and user template are in the same folder. Provision schema as administrator; runtime permissions are own-database CRUD.

After project setup, run from the root in its own PowerShell terminal:

```powershell
.\.venv\Scripts\python.exe services\notification\run.py
```

The launcher reads this folder's `.env`. Dependencies are declared in composer.json (built-in PHP extensions; no external packages). Configuration examples are in `.env.example`.

Windows uses a private XAMPP Apache instance for actual concurrent PHP requests. The standalone run.py uses only Python's standard library as a process/configuration launcher; all service business logic is PHP. Linux verification uses PHP's multi-worker development server. The public document root is `public/`; configuration/source remains outside it.

Read the root README and [beginner guide](../../docs/BEGINNER_WINDOWS_GUIDE.md) for software, SQL, testing and video steps.
