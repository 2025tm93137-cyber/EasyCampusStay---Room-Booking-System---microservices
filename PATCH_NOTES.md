# Applying this continuation to an existing repository
Do not delete your existing Assignment 1 repository or import its Git history again.
This package is based on the last supplied source; it does not include unprovided newer GitHub commits.
Create a branch, copy new deployment files, and review the three existing-file edits before merging.

New: `docker-compose.yml`, `.dockerignore`, `.env.example`, `.gitattributes`, each application Dockerfile, `deploy/`, `k8s/`, Assignment 2 documentation.
Existing edits:
- `ui/bootstrap.php`: environment URLs are read even when no local .env exists; an explicit upstream host allow-list supports Docker DNS while defaulting to the original loopback-only mode.
- `services/payment/src/platform.php`: optional LOG_STDOUT sends structured events to stderr for container logs; local file logging remains the default.
- `services/notification/src/platform.php`: same optional logging change.
- `.gitignore`: private generated configuration and runtime evidence exclusions.
The supplied frontend already uses Easy Campus Stay. Technical database names remain campusstay_*.

Use `deploy/patches/assignment2-existing-files.patch` to inspect the actual differences to the supplied baseline.
Only apply it automatically if `git apply --check` succeeds against your current files. Otherwise merge these small edits manually.
No service business rules or schema definitions were changed for containerization.
Root README is Assignment 2 specific; retain your existing Assignment 1 guide alongside it as needed.
The container-focused full ZIP excludes the old Windows offline wheels and old generated reports.

## Windows import helper added 31 October 2026
+Use deploy/import_assignment2.py from the separately extracted package. Preview first.
+It verifies the deployment-file manifest, checks existing-file patches, keeps private .env untouched,
+refuses an unclean checkout and stops before incompatible changes. Different deployment files
+require explicit --replace-reviewed after review and are backed up outside the repository.
+README_ASSIGNMENT2.md is added without overwriting the existing checkout README.
+Add a link from the root README to that deployment guide before submission.
+No business-rule files or schema definitions were changed by this documentation update.
+