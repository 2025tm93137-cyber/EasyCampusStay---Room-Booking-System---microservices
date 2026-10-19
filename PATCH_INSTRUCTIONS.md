# Windows worker startup fix

This patch addresses the reported WinError 10022 at sock.listen in a spawned Uvicorn worker. The starter configuration requested two workers. The patch uses one Python worker on Windows to avoid the shared-listening-socket path, while retaining the configured worker count on Linux. It also records the effective worker counts in test evidence.

Windows itself has not been executed in the automated validation environment. The supplied screenshot shows the Windows failure; please verify startup and run the full suite on your machine after applying the fix. The exact underlying Windows socket/provider issue is not proven by the screenshot alone.

## Apply to your existing project

1. Stop the assignment launchers using Ctrl+C in their own PowerShell windows. Keep XAMPP MySQL running.
2. Save CampusStay_Windows_Worker_Startup_Fix.zip in your Downloads folder.
3. Open a new PowerShell window and run the following single command. It replaces only services/inventory/run.py, services/reservation/run.py and scripts/run_all.py, and adds these instructions plus validation metadata.

```powershell
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\CampusStay_Windows_Worker_Startup_Fix.zip" -DestinationPath 'C:\Projects\campusstay_option_b' -Force
```

4. Run the environment check and, if it passes, start the application:

```powershell
Set-Location 'C:\Projects\campusstay_option_b'
.\.venv\Scripts\python.exe scripts\doctor.py --require-stopped --apache-check
.\.venv\Scripts\python.exe scripts\run.py
```

5. Keep the launcher open. Check http://127.0.0.1:8101/health and http://127.0.0.1:8102/health, then open http://127.0.0.1:8180/.
6. Stop the normal launcher before running scripts/run_all.py. That suite owns its own service processes. The generated Windows run_summary.json should record one Python worker per Python service.
7. Review the patch, rerun your own tests and commit the actual changes to your repository with an accurate message such as "Fix Windows Python worker startup with AI-assisted patch".

The patch contains no database credentials, and no database reinitialisation is required. Four business services and separate databases remain. A single worker still supports concurrent API requests; the existing 20-request capacity and simultaneous-idempotency scripts must pass on the submission machine. Do not describe this as a production load benchmark.

Files replaced:
- services/inventory/run.py
- services/reservation/run.py
- scripts/run_all.py

This patch is AI-assisted. Its included validation metadata identifies the actual platform. Prior shipped source hashes predate the patch; regenerate evidence after applying it.
