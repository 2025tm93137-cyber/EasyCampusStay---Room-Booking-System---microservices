FROM php:8.3-apache-bookworm
# cURL is built into the official PHP Apache image; only PDO MySQL is added.
RUN docker-php-ext-install pdo_mysql \
    && php -r "exit(extension_loaded('curl') && extension_loaded('pdo_mysql') ? 0 : 1);"
ENV LOG_STDOUT=true
WORKDIR /app/services/notification
COPY services/notification/public ./public
COPY services/notification/src ./src
COPY services/notification/openapi.json ./openapi.json

COPY deploy/apache.conf /etc/apache2/sites-available/000-default.conf
RUN sed -i 's/Listen 80/Listen 8080/' /etc/apache2/ports.conf \
    && mkdir -p logs .runtime/sessions \
    && chown -R www-data:www-data logs .runtime
RUN ln -s "$PWD/public" /var/www/easystay-public
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=4s --start-period=30s --retries=6 CMD php -r "exit(@file_get_contents('http://127.0.0.1:8080/health')===false ? 1 : 0);"
CMD ["apache2-foreground"]
