# Deployment files
Docker Compose uses one MariaDB engine with four restricted databases, matching Assignment 1.
The db-init administrator container exits after provisioning. Each application receives only its own database password.
The optional tools container receives all FOUR SERVICE passwords for diagnostic assertions, never the root password.
It is not part of the request path. Do not expose a Docker socket or publish MariaDB.
Images copy only explicit source files, never local .env files. Root .env is read by Compose on the host.
Image tags pin supported minor release families; registry tags can move. Record image digests in your own evidence for exact replication.
php:8.3-apache supplies a concurrent PHP server; no PHP development server is used in containers.
Application processes communicate by Compose/Kubernetes DNS names, never host localhost.
UI_ALLOWED_UPSTREAM_HOSTS explicitly limits the UI proxy to the four configured API hosts.
Database initialization uses CREATE TABLE IF NOT EXISTS; it does not delete existing bookings and is not a general schema migration system.
Keep .env stable for an existing database volume. Changing the root password in .env does not change an existing MariaDB root account.
Use docker compose down (without -v) to retain data. down -v deletes the project database volume.
