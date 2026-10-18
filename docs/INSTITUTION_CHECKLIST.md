# Institution requirement mapping and final checklist

Source: Assignment1_Microservices_Design_and_Development.docx, SEZG583 Assignment 1. This checklist maps the implemented scope to that brief; it does not override faculty instructions.

| Requirement | Implementation / evidence |
|---|---|
| At least four business services | Inventory, Reservation, Payment and Notification in services/ |
| Independently runnable; own dependencies/config | Own run.py, source, SQL, tests, .env.example; Python requirements.lock.txt or PHP composer.json |
| Transaction spans at least three services | Reservation orchestrates Inventory, Payment and Notification via HTTP |
| Contended resource | Room type/date stock; Inventory atomic conditional decrement |
| Unsafe-to-repeat operation | Booking and mock charge; request key, fingerprint, response cache and unique business IDs |
| Slow/failing dependency | Local PHP Payment decline/slow modes and Notification fail_once |
| Database per service, separate credentials | Four campusstay_* databases; cs_* accounts; all 12 peer accesses denied in additional_checks.json |
| No cross-service joins/FKs | Service SQL contains only own tables; APIs carry peer entity IDs |
| REST, versioned APIs, validation, errors, OpenAPI | /api/v1 paths and /openapi.json on each service; docs/openapi copies |
| /health, env settings, correlation logs | Four /health endpoints, generated own .env, structured logs propagated by saga |
| Four or more traceable business rules | Eight BRs in README and report; rules/tests mapped by function |
| Unit and end-to-end tests | 26 Python business cases, 14 native PHP cases, nine configuration/launcher cases; scripts/e2e.py |
| Challenge 1: at least 20 parallel requests | scripts/challenge_concurrency.py and evidence/challenge-1-concurrency/ |
| Challenge 2: sequential and simultaneous idempotency | scripts/challenge_idempotency.py and evidence/challenge-2-idempotency/ |
| Chosen Challenge 3C | scripts/challenge_saga.py and evidence/challenge-3c-saga/ |
| Evidence with failure cases | Declined payment/compensation; wrong password, denied peer DB access, stopped Payment/Notification and timeout recovery |
| Source repository faculty can view | Team must create/push its real repository and verify access |
| Report max 15 main pages, excluding appendices | docs/CampusStay_Design_Report.pdf; complete actual personal fields first |
| 8-10 minute live video; every member speaks | DEMO_VIDEO_GUIDE.md/PDF; team records and uploads its own demonstration |
| Contributions and half-page reflections | Actual entries in submission.json; each member writes own docs/reflections file |
| AI-use declaration | AI_USE_DECLARATION.md and report appendix disclose substantial initial assistance |
| Assignment 2 readiness | Config/env/health/ownership support later containers; Docker/Minikube deployment is not claimed here |

## Team actions still required before submission

- [ ] Read and explain all service behavior and business rules.
- [ ] Make and document genuine contributions with each member's real Git identity.
- [ ] Run the project and full suite on the Windows/XAMPP recording machine.
- [ ] Check a fresh clone using the README.
- [ ] Review test outputs and collect your own current evidence.
- [ ] Fill names, IDs, responsibility/contribution entries and links.
- [ ] Write each half-page personal reflection.
- [ ] Keep an accurate AI-use declaration.
- [ ] Rebuild/inspect the report and verify its main-page limit.
- [ ] Record an 8-10 minute live demonstration with every member speaking.
- [ ] Verify faculty access to GitHub and Drive/video links.
- [ ] Submit the exact required items through the institution portal.

The shipped execution evidence is real Linux PHP/MariaDB verification. It must not be described as a native Windows run. run_all.py records the actual platform and source hashes when you run it locally.
