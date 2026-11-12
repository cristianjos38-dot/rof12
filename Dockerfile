FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS builder
WORKDIR /app
COPY pyproject.toml .
COPY app app
COPY scripts scripts
COPY migrations migrations
COPY alembic.ini .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app app
COPY scripts scripts
COPY migrations migrations
COPY alembic.ini .
RUN groupadd --system --gid 10001 rof12 \
    && useradd --system --uid 10001 --gid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin rof12 \
    && mkdir -p /var/lib/rof12/documents \
    && chown -R rof12:rof12 /app /var/lib/rof12
ENV MODEL_MODE=mock PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

