# CampusStay: Python + PHP microservices on XAMPP

CampusStay models one room for one night in a campus guesthouse. Inventory and Reservation are Python/FastAPI services. Payment and Notification are independently runnable PHP mock services. A small PHP browser console calls their APIs. Four separate MySQL/MariaDB databases and four separate application logins enforce service boundaries.

Start with **docs/BEGINNER_WINDOWS_GUIDE.md** or its PDF. It covers software installation, Git/GitHub, SQL setup, running the UI, all tests, the report and the institution's 8-10 minute video.

## Windows quick start

Install 64-bit Python 3.12 and XAMPP with PHP 8.0 or later; a current PHP 8.2 XAMPP package is the recommended local target. Start XAMPP's **MySQL** component. XAMPP bundles MariaDB behind this label. Its main Apache component is useful for phpMyAdmin; the application launchers start their own Apache instances on separate ports.

From the extracted project root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links windows\wheels -r requirements-windows.txt
.\.venv\Scripts\python.exe scripts\configure.py
.\.venv\Scripts\python.exe scripts\init_databases.py
.\.venv\Scripts\python.exe scripts\doctor.py --require-stopped --apache-check
.\.venv\Scripts\python.exe scripts\run.py
```

Open **http://127.0.0.1:8180/**. Keep the launcher window open. Ctrl+C stops its owned processes. No batch files or PowerShell activation script are required.

If XAMPP is installed elsewhere or its database uses another port, use your actual values during initial configuration:

```powershell
.\.venv\Scripts\python.exe scripts\configure.py --xampp D:\xampp --db-port 3307
```

Existing configuration is retained. `--force` deliberately regenerates it; rerun `init_databases.py` after a deliberate password regeneration. No setup script drops databases or tables. Existing application users with privileges outside their own project database are rejected by the setup script.

## Services and data ownership

| Service | Language | API address | Database | Runtime login |
|---|---|---|---|---|
| Inventory | Python | http://127.0.0.1:8101 | campusstay_inventory | cs_inventory |
| Reservation | Python | http://127.0.0.1:8102 | campusstay_reservation | cs_reservation |
| Payment mock | PHP | http://127.0.0.1:8103 | campusstay_payment | cs_payment |
| Notification mock | PHP | http://127.0.0.1:8104 | campusstay_notification | cs_notification |

Every service exposes `/health` and `/openapi.json`, has its own folder/configuration/dependency file and imports only its own database schema. Each runtime login has SELECT/INSERT/UPDATE/DELETE on its own database only. Database provisioning is a separate administrator task. Services never read peer tables. Payment and notification never contact real providers.

The UI has no database credentials and is an optional API client, not a fifth business service. It provides room inventory creation, availability, bookings, status lookup, original-request replay and changed-payload conflict demonstrations. Every request is local; assets and fonts have no CDN dependency.

## Run services independently

From the project root, run one command per terminal:

```powershell
.\.venv\Scripts\python.exe services\inventory\run.py
.\.venv\Scripts\python.exe services\payment\run.py
.\.venv\Scripts\python.exe services\notification\run.py
.\.venv\Scripts\python.exe services\reservation\run.py
.\.venv\Scripts\python.exe ui\run.py
```

Each PHP folder contains its complete PHP source and a standalone standard-library Python launcher. On Windows it generates a private Apache configuration using the XAMPP runtime, serves only `public`, and owns its separate process tree. It does not edit the global XAMPP Apache configuration. Each service can also run independently with PHP's built-in development server; on Windows that server is single-worker, so use the supplied Apache launcher for concurrent PHP tests. Linux verification uses PHP's multi-worker development server. Actual runtimes are recorded with evidence.

## Demonstrate and validate

With services running, open another terminal at the root:

```powershell
.\.venv\Scripts\python.exe scripts\e2e.py
.\.venv\Scripts\python.exe scripts\challenge_concurrency.py --requests 20 --capacity 5
.\.venv\Scripts\python.exe scripts\challenge_idempotency.py
.\.venv\Scripts\python.exe scripts\challenge_saga.py
```

Stop the normal launcher first, then run the suite, which owns its own processes:

```powershell
.\.venv\Scripts\python.exe scripts\run_all.py
```

There are 40 business-rule cases: 26 in Python and 14 in native PHP. Nine additional Python tests cover credential generation and process ownership. The suite also runs the API workflow, all three challenges, 12 denied peer-database connections, different-key business uniqueness, wrong-password checks, real stopped-service recovery and immutable POST responses after recovery. It saves raw outputs, SQL snapshots, structured logs and actual OS/runtime/source hashes in `evidence`.

The delivered run is on Linux with PHP 8.3 and MariaDB 10.11. Windows Apache configuration/launching needs execution on your own XAMPP installation. Run the suite there and use your own evidence for the final demonstration. No native Windows execution is claimed by the supplied Linux evidence.

## Business rules

| Rule | Meaning | Code | Main verification |
|---|---|---|---|
| BR1 | Stay date is today or later | Inventory/Reservation rules.py | Python rule tests; invalid past-date API check |
| BR2 | Stock stays between zero and capacity | Inventory repository.reserve and SQL CHECK | Python decision tests; 20-request database challenge |
| BR3 | One key maps to one semantic request and immutable response | Python/PHP local_idempotent; Reservation claim/cache | Fingerprint tests; simultaneous first-request challenge |
| BR4 | Only paid bookings become CONFIRMED | Reservation rules.py and saga.py | Transition tests; end-to-end workflow |
| BR5 | Release happens once; paid bookings require refund before compensation | Reservation rules; Inventory change_hold | Compensation tests and database state |
| BR6 | Charge amount is a positive integer in minor units | Payment src/rules.php | Native PHP amount tests |
| BR7 | Only charged payments can be refunded; repeats create one refund | Payment rules.php/repository.php | Native PHP rules; concurrent different-key refund check |
| BR8 | Confirmation requires a confirmed booking state | Notification src/rules.php | Native PHP rules; successful/retried notification flow |

## Important decisions

- Inventory's conditional SQL decrement arbitrates capacity. Checking availability in application memory would race.
- A local operation records its effect and idempotency response in one InnoDB transaction. A namespace-scoped GET_LOCK serializes the key; UNIQUE constraints independently prevent repeated business effects under different keys.
- Connections use READ COMMITTED so a query after acquiring a contended named lock sees the preceding owner's committed row.
- Reservation persists an explicit saga. Its session lock is on an autocommit connection; no database transaction remains open during downstream HTTP calls. Retries use stable keys derived from the booking ID.
- A payment timeout returns a cached 202 acceptance; GET shows subsequent progress. Unknown payment outcome retains the room until resolved. Notification failure preserves a confirmed, paid booking.
- PHP infrastructure is vendored into each PHP service; Python's adapter is likewise local. `scripts/vendor_platform.py` synchronises infrastructure copies without sharing runtime business state.

## Repository map

| Folder | Contents |
|---|---|
| services/inventory, services/reservation | Independent Python source, rules, repository, SQL, tests, environment example and locked dependencies |
| services/payment, services/notification | Independent PHP source/public entry point, SQL, native tests, environment example and composer.json |
| ui | Optional PHP API client and local CSS/JavaScript |
| scripts | Configuration, provisioning, diagnostics, supervisor and repeatable evidence clients |
| docs | Beginner guide, report, diagrams, OpenAPI, video plan, personal contribution and AI-use materials |
| evidence | Real recorded outputs, one challenge folder per claim, plus tests |
| windows/wheels | Bundled Python 3.12 Windows dependencies |
| tools | Reproducible documentation and stateless infrastructure templates |

## Institution alignment and genuine student work

This implements Assignment 1: four services, main transaction, Challenges 1 and 2 plus chosen Challenge 3C. Authentication, real payment/email and a full customer UI are outside scope. Docker/Minikube deployment is Assignment 2 and is future work here.

The initial implementation and documentation are substantially AI-assisted and adapted from the earlier PostgreSQL prototype. See `docs/AI_USE_DECLARATION.md`. No plagiarism score, independent authorship or student contribution history is claimed. Each team member must understand, review, make genuine contributions, run the work and explain it in the video. Complete actual names, IDs, repository/video links, contribution entries and personal reflections before submission. `docs/EXPLAIN_AND_PERSONALISE.md` helps you do this through substantive work rather than cosmetic renaming.

The report PDF is a draft until these personal/submission fields are completed. `docs/INSTITUTION_CHECKLIST.md` maps requirements to actual files and verification commands.

## Linux verification alternative

Use a running local MariaDB 10.4+ server and PHP 8.0+ with pdo_mysql/curl. Install Python dependencies from requirements.lock.txt, configure the real database host/port and set PHP_BINARY if PHP is not on PATH. The same scripts run on Linux. PHP launchers use four development workers there. This is an execution alternative for validation, not a claim that the Windows-specific Apache branch has run.

## References

- XAMPP Windows FAQ: https://www.apachefriends.org/faq_windows.html
- MariaDB GET_LOCK: https://mariadb.com/docs/server/reference/sql-functions/secondary-functions/miscellaneous-functions/get_lock
- PHP development server limitations: https://www.php.net/manual/en/features.commandline.webserver.php
- Git basics: https://git-scm.com/book/en/v2/Git-Basics-Getting-a-Git-Repository

## Assignment 2: Docker deployment

See [Assignment 2 deployment guide](README_ASSIGNMENT2.md).
