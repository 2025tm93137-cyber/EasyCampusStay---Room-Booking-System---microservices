# Evidence index and provenance

The shipped evidence was produced by actual Python, native PHP and MariaDB/InnoDB execution on Linux. It does not claim native Windows/XAMPP execution. Exact versions, timestamps, command exits and source SHA-256 values are in tests/run_summary.json. UI results have their own timestamp in tests/ui_validation.json. Synthetic IDs, visitors and example.test recipients are used throughout.

| Folder/file | Claim supported | Main files |
|---|---|---|
| challenge-1-concurrency | 20 parallel requests against capacity five: exactly five successes, no oversell | results.json, database_state.json, output.txt, service logs |
| challenge-2-idempotency | Three sequential replays, 20 simultaneous first calls, changed-payload 409, one business effect | results.json, database_state.json, output.txt, service logs |
| challenge-3c-saga | Decline at step 3; durable compensation restores stock; repeated release is safe | initial_check.json, database_after_compensation.json, database_after_repeated_compensation.json, results.json, output.txt, logs |
| tests/unit_tests.txt and unit_tests.xml | 26 Python business cases plus nine configuration/process cases | Real pytest output/JUnit |
| tests/payment_unit_tests.txt | Ten native PHP business-rule cases | PHP test output |
| tests/notification_unit_tests.txt | Four native PHP business-rule cases | PHP test output |
| tests/e2e.json | Successful/declined/slow booking and notification retry | API responses and assertions |
| tests/additional_checks.json | 12 denied peer DB connections; wrong password; different-key uniqueness; validation | Actual SQL/API checks |
| tests/recovery_checks.json | Actual stopped Payment/Notification recovery; immutable cached POST after recovery | Three recorded scenarios |
| tests/ui_validation.json | Ten live Chromium checks including responsive layout and no JavaScript errors | Actual UI test metadata |
| tests/package_validation.json | Clean Git clone, no secret/runtime files, syntax and dependency completeness | Packaging-time checks |

Use your own machine's results for the final video. With XAMPP MySQL running and the normal app launcher stopped, run scripts/run_all.py from the configured project root. It starts/stops its own service processes and regenerates challenge/API evidence with fresh synthetic IDs. For individual challenge commands keep scripts/run.py running. Read raw results and SQL snapshots, not only PASS lines. Record terminal command, output and timestamp in any screenshots required by the brief.

The chosen extra challenge is 3C. Supplementary outage tests do not claim complete implementation of all alternatives 3A-3D. A packaging-time Git clone is automated verification and is not presented as a student's contribution history.
