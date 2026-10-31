# Genuine deployment incident record
Complete this using an actual issue encountered by your team during Docker deployment.
Do not copy expected results as evidence. The optional localhost override is a disclosed injected exercise.

1. Date/time, operator, Windows build, Docker/Compose versions: TO COMPLETE.
2. Exact command or UI action that failed: TO COMPLETE.
3. Observed symptom and booking ID, if relevant: TO COMPLETE.
4. Evidence paths for docker compose ps and logs: TO COMPLETE.
5. Diagnosis command(s), actual output and why it identifies the cause: TO COMPLETE.
6. Root cause, including the incorrect configuration line if relevant: TO COMPLETE.
7. Actual fix and Git commit reference: TO COMPLETE.
8. Same workflow retest and successful evidence path: TO COMPLETE.
9. What the team learned and how it would prevent recurrence: TO COMPLETE.

Useful concept: localhost means the current container. Compose service DNS names identify other services.
A healthy /health may check only the local DB; prove downstream reachability using an actual booking.
Never include passwords, full Secret manifests or complete environment dumps in incident evidence.
