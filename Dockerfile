FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    C360_DATA_DIR=/app/data \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's|http://deb.debian.org/debian-security|https://deb.debian.org/debian-security|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data /app/output /tmp/matplotlib \
    && chown -R appuser:appuser /app /tmp/matplotlib

# Install Python dependencies
COPY requirements.txt requirements-lock.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Copy the complete project
COPY --chown=appuser:appuser . /app

# Copy Docker entrypoint
COPY --chown=appuser:appuser docker/entrypoint.sh /usr/local/bin/customer360-entrypoint

RUN chmod 755 /usr/local/bin/customer360-entrypoint \
    && mkdir -p /app/data /app/output \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8501/_stcore/health || exit 1

ENTRYPOINT ["customer360-entrypoint"]