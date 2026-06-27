FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_RETRIES=3
ARG PIP_TIMEOUT=30

COPY requirements.txt .

RUN python -m pip install --no-cache-dir \
    --prefer-binary \
    --retries "$PIP_RETRIES" \
    --timeout "$PIP_TIMEOUT" \
    --index-url "$PIP_INDEX_URL" \
    -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
