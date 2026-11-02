FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY app app
COPY scripts scripts
RUN pip install --no-cache-dir .
ENV MODEL_MODE=mock PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

