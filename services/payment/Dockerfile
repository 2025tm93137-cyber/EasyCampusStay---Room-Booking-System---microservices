# Base image: official PHP 8.3 with Apache preinstalled, built on Debian Bookworm.
# Pinning the PHP minor version and the Debian release keeps builds reproducible.
FROM php:8.3-apache-bookworm

# Install the PDO MySQL extension so the service can talk to the MySQL database.
# cURL is already bundled in the official image (used for outbound HTTP calls),
# so only pdo_mysql is added here.
# The trailing php -r check fails the build early if either extension is missing,
# instead of letting the problem surface at runtime.
RUN docker-php-ext-install pdo_mysql \
    && php -r "exit(extension_loaded('curl') && extension_loaded('pdo_mysql') ? 0 : 1);"

# Send application logs to stdout/stderr so `docker logs` and any log collector
# can read them, rather than writing only to files inside the container.
ENV LOG_STDOUT=true

# All following relative paths resolve under this directory, which mirrors the
# service's location in the monorepo (services/payment).
WORKDIR /app/services/payment

# Copy only what the service needs at runtime:
#   public/       web root (entry point served by Apache)
#   src/          application source code
#   openapi.json  API contract/specification for the Payment service
COPY services/payment/public ./public
COPY services/payment/src ./src
COPY services/payment/openapi.json ./openapi.json

# Replace the default Apache virtual host with the project's own configuration
# (document root, rewrite rules, logging, etc.).
COPY deploy/apache.conf /etc/apache2/sites-available/000-default.conf

# Run Apache on port 8080 instead of 80. Ports below 1024 are privileged, and
# 8080 is the conventional non-privileged port for containerised web services.
# Also create the writable folders for logs and PHP sessions, and give ownership
# to www-data, the user Apache runs as, so the app can write to them.
RUN sed -i 's/Listen 80/Listen 8080/' /etc/apache2/ports.conf \
    && mkdir -p logs .runtime/sessions \
    && chown -R www-data:www-data logs .runtime

# Expose the public folder under /var/www/easystay-public via a symlink so the
# Apache config can reference a stable path regardless of WORKDIR.
RUN ln -s "$PWD/public" /var/www/easystay-public

# Document the internal port the container listens on (must match the Listen
# directive above). EXPOSE is informational; publishing the port is done with
# `-p` or in docker-compose.
EXPOSE 8080

# Health check: every 10s, request /health on localhost inside the container.
# - timeout 4s: a slow response counts as a failure
# - start-period 30s: grace period while Apache and PHP start up
# - retries 6: mark the container unhealthy only after 6 consecutive failures
# `@` suppresses PHP warnings; a failed request (false) returns exit code 1.
HEALTHCHECK --interval=10s --timeout=4s --start-period=30s --retries=6 CMD php -r "exit(@file_get_contents('http://127.0.0.1:8080/health')===false ? 1 : 0);"

# Start Apache in the foreground so it stays as the container's main process.
# If it ran as a daemon, the container would exit immediately.
CMD ["apache2-foreground"]
