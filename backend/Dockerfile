FROM python:3.13-slim

ARG APT_MIRROR_HOST=mirrors.tuna.tsinghua.edu.cn
ARG PIP_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=${PIP_INDEX_URL}

WORKDIR /app

RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i "s|deb.debian.org|${APT_MIRROR_HOST}|g; s|security.debian.org|${APT_MIRROR_HOST}|g" /etc/apt/sources.list.d/debian.sources; \
    fi \
    && addgroup --system app \
    && adduser --system --ingroup app app \
    && mkdir -p /data/object-store \
    && chown -R app:app /app /data

COPY pyproject.toml ./
COPY backend ./backend

RUN pip install --no-cache-dir .

EXPOSE 8000

ENV DROS_LEDGER_BACKEND=postgres \
    DROS_POSTGRES_SCHEMA=dr_os_dev \
    DROS_OBJECT_STORE_PATH=/data/object-store

USER app

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
