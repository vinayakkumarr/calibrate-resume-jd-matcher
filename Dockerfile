# ==============================================================================
# Calibrate: Production Dual-Engine Container
# Base: Debian Bookworm with PHP 8.2 (Apache) & Python 3.11 Runtime
# Target Host: Koyeb (Eco Tier 512MB RAM) | Free Cloud MySQL (TiDB Serverless)
# ==============================================================================

FROM php:8.2-apache-bookworm

# ------------------------------------------------------------------------------
# 1. System Dependencies, Process Reaper (tini), & CA Certificates
# ------------------------------------------------------------------------------
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=80

RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    python3 \
    python3-pip \
    python3-venv \
    ca-certificates \
    && docker-php-ext-install -j$(nproc) pdo_mysql fileinfo opcache \
    && a2enmod rewrite headers \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# ------------------------------------------------------------------------------
# 2. Apache & OPcache Tuning for Low-Memory Stability (512MB RAM Limit)
# ------------------------------------------------------------------------------
# Enforce strict DocumentRoot isolation to public/
ENV APACHE_DOCUMENT_ROOT=/var/www/html/public
RUN sed -ri -e 's!/var/www/html!${APACHE_DOCUMENT_ROOT}!g' /etc/apache2/sites-available/*.conf \
    && sed -ri -e 's!/var/www/!${APACHE_DOCUMENT_ROOT}!g' /etc/apache2/apache2.conf /etc/apache2/conf-available/*.conf

# Configure native environment-based port binding (Koyeb $PORT support)
RUN echo "Listen \${PORT}" > /etc/apache2/ports.conf \
    && sed -ri -e 's!<VirtualHost \*:80>!<VirtualHost *:${PORT}>!g' /etc/apache2/sites-available/000-default.conf

# Security & Concurrency Hardening (Apache Prefork tuned for 512MB)
RUN echo "ServerTokens Prod\nServerSignature Off" > /etc/apache2/conf-available/security_hardening.conf \
    && echo "<IfModule mpm_prefork_module>\n\
    StartServers             2\n\
    MinSpareServers          2\n\
    MaxSpareServers          4\n\
    MaxRequestWorkers        10\n\
    MaxConnectionsPerChild   1000\n\
</IfModule>" > /etc/apache2/conf-available/mpm_prefork_tuning.conf \
    && a2enconf security_hardening mpm_prefork_tuning

# Production PHP engine configuration, OPcache bytecode caching, and EGPCS exposure
RUN cp "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini" \
    && echo "variables_order = \"EGPCS\"\n\
upload_max_filesize = 12M\n\
post_max_size = 15M\n\
memory_limit = 128M\n\
max_execution_time = 60\n\
display_errors = Off\n\
log_errors = On\n\
error_log = /dev/stderr\n\
opcache.enable = 1\n\
opcache.enable_cli = 0\n\
opcache.memory_consumption = 32\n\
opcache.interned_strings_buffer = 8\n\
opcache.max_accelerated_files = 2000\n\
opcache.validate_timestamps = 0" > "$PHP_INI_DIR/conf.d/production.ini"

# ------------------------------------------------------------------------------
# 3. Python Virtual Environment & Layer-Cached Dependencies
# ------------------------------------------------------------------------------
WORKDIR /var/www/html

COPY engine/requirements.txt ./engine/requirements.txt

RUN python3 -m venv ./engine/venv \
    && ./engine/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel \
    && ./engine/venv/bin/pip install --no-cache-dir -r ./engine/requirements.txt

# ------------------------------------------------------------------------------
# 4. Application Source & Storage Hardening
# ------------------------------------------------------------------------------
COPY . .

RUN mkdir -p storage/uploads storage/logs \
    && chown -R www-data:www-data storage \
    && chmod -R 775 storage \
    && chmod -R 755 engine \
    && sed -i 's/\r$//' docker-entrypoint.sh \
    && chmod +x docker-entrypoint.sh

EXPOSE ${PORT}

# Tini as PID 1 reaps background Python workers and supervises entrypoint
ENTRYPOINT ["/usr/bin/tini", "--", "/var/www/html/docker-entrypoint.sh"]
CMD ["apache2-foreground"]
