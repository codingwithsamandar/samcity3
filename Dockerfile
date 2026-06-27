# ═══════════════════════════════════════════════════════════════════
#  SamCity — Django (ASGI/daphne) production image (multi-stage)
# ═══════════════════════════════════════════════════════════════════

# ── 1-bosqich: bog'liqliklarni wheel'larga yig'amiz ──
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels
COPY requirements.txt .
RUN pip wheel --wheel-dir=/wheels -r requirements.txt


# ── 2-bosqich: yengil runtime image ──
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=sdev.settings \
    PORT=8000

# libpq runtime kutubxonasi (psycopg uchun)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Wheel'lardan o'rnatamiz (internetsiz, tez)
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Non-root foydalanuvchi
RUN useradd --create-home --uid 1000 appuser
WORKDIR /app
COPY --chown=appuser:appuser . .

# Build vaqtida statik fayllarni yig'amiz (SECRET_KEY shart, lekin maxfiy emas — build-only)
RUN DJANGO_DEBUG=False DJANGO_SECRET_KEY=build-time-dummy-key \
    python manage.py collectstatic --noinput

RUN chmod +x entrypoint.sh && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Konteyner sog'lig'i (nginx/compose ham tekshiradi)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health/ || exit 1

ENTRYPOINT ["./entrypoint.sh"]
