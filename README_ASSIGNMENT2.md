# Easy Campus Stay Assignment 2
A simple room-booking system for campus visitors. Group 22. Python and PHP services, a browser UI and MariaDB in Docker.

## Start here on Windows with Docker Desktop already installed
Read docs/ASSIGNMENT2_WINDOWS_GUIDE.md one numbered section at a time.
Your existing checkout is C:\Projects\campusstay_assignment2.
If deploy/configure.py is missing, complete the package extraction and preview/import steps first.

The Git repository is https://github.com/2025tm93137-cyber/EasyCampusStay---Room-Booking-System---microservices.
This ZIP extends the supplied Assignment 1 baseline; it is not an authenticated checkout of your latest GitHub branch.
Keep the extracted package separate from your existing Git checkout and preserve newer member work.

## Import deployment additions into your existing checkout
From PowerShell, after extracting this ZIP into C:\Projects\EasyCampusStay_A2_Package:

```powershell
$A2Package = 'C:\Projects\EasyCampusStay_A2_Package'
$A2Source = Join-Path $A2Package 'Easy_Campus_Stay_Assignment2'
py -3.12 "$A2Source\deploy\import_assignment2.py" --target 'C:\Projects\campusstay_assignment2'
```

This is a preview. Review the files and compatible existing-file patches, create your Assignment 2 branch,
and follow sections 5-6 before applying. The helper refuses a dirty working tree or incompatible patches.
Different deployment files need the explicit --replace-reviewed option after review; previous files are backed up.
The helper never imports private .env files, changes database data, commits, pushes, or replaces business-rule modules.

## Start the complete deployment
Stop the old Assignment 1 launcher. Docker Desktop needs a running Linux engine.
From the checked project root:

```powershell
py -3.12 deploy/configure.py
git check-ignore .env
docker compose config --quiet
docker compose up --build
```

Configuration generates private passwords once without printing them. Keep the same .env for retained database data.
There is no database password prompt. Do not commit .env or show it in the video.
No host venv, offline wheels, Composer installation or XAMPP database is required for this Docker workflow.
The first build requires Internet access.

Open http://127.0.0.1:8180/ after health checks pass. Six containers stay running: db, four APIs and ui.
db-init Exited (0) is expected setup completion, not an application failure.
API host ports are 8101-8104; their /health endpoints check service database access.
The UI /health checks its process. A working booking proves cross-service communication.
All APIs use port 8080 inside the Docker network. One MariaDB container holds four restricted service databases.

## Check workflows and restart
In Terminal B, at the same project root:

```powershell
docker compose ps -a
docker compose --profile test run --rm --build tools
docker compose down
docker compose up -d
```

The tools container runs booking, concurrency, idempotency, saga and 12 peer-database isolation assertions.
Its summary is evidence/assignment2/workflow_summary.json.
Retrieve a booking created BEFORE restart to prove persistence. Do not use down -v for this check.
Do not run scripts/run_all.py or scripts/run.py alongside this deployment.
Some old UI help text refers to Assignment 1 service terminals; use this Docker guide for Assignment 2.

## Troubleshooting and the optional extension
Record a genuine deployment incident in docs/TROUBLESHOOTING_WORKSHEET.md.
The earlier missing deploy/configure.py error is a setup issue before Docker starts; it alone does not complete Task 3.
The included localhost override is a disclosed injected rehearsal, not an unplanned incident.

Minikube steps are separate and optional. Stop Compose first on the practice laptop and before using port 8180.
Use Deploy-Minikube.ps1, a dedicated UI port-forward, Demonstrate-SelfHealing.ps1 and Check-Minikube.ps1.
Show a working Kubernetes booking, three Inventory replicas, the deleted/replacement pod UID and a working workflow afterward.
This demonstrates manual scaling and Deployment recovery, not HPA.

## Documentation and submission
- docs/ASSIGNMENT2_WINDOWS_GUIDE.md: all installation/run commands, expected results and fixes.
- docs/ASSIGNMENT2_VIDEO_GUIDE.md: simple speech, times, commands, files and four-member roles.
- docs/submission/: matching PDFs and editable Word deployment report.
- docs/CONTRIBUTIONS_AND_AI.md: assigned work and accurate AI disclosure.
- PATCH_NOTES.md: the small existing-file changes needed for Docker.
- deploy/import_manifest.json: the precise deployment-file import list and source hashes.

If importing into an older checkout, add a link from its root README.md to README_ASSIGNMENT2.md so reviewers can find these steps.
The report has five main pages plus an appendix for actual run records. Complete the pending team evidence and real Assignment 2 commit references.
The institution recommends a 6-8 minute demo. Mujaffar operates the Teams shared desktop; all four explain real work.

## Validation status
The supplied earlier native Linux reference run passed 35 Python cases, 10 Payment cases, four Notification cases,
four API/challenge scripts, UI configuration checks and 12 denied peer-database accesses.
Those results are not Windows Docker or Kubernetes evidence.
This documentation revision also checks importer safeguards, Compose configuration, manifest schemas and PowerShell syntax.
No Docker daemon or Kubernetes cluster is available in this authoring environment, so container builds, Windows execution,
restart persistence and cluster recovery remain for your team's actual run. Record only results you observe.

## Official references
- https://docs.docker.com/desktop/setup/install/windows-install/
- https://docs.docker.com/compose/how-tos/startup-order/
- https://docs.docker.com/compose/how-tos/networking/
- https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
- https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/
- https://minikube.sigs.k8s.io/docs/start/
- https://minikube.sigs.k8s.io/docs/drivers/docker/
- https://minikube.sigs.k8s.io/docs/commands/image/
