# ---- Stage 1: builder ----
FROM python:3.12-slim AS builder
WORKDIR /app

COPY requirements-docker.txt .
RUN pip install --user --no-cache-dir -r requirements-docker.txt

# ---- Stage 2: runtime ----
FROM python:3.12-slim
WORKDIR /app

RUN useradd --create-home appuser
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

COPY agent/ ./agent/
COPY api/ ./api/
COPY memory/ ./memory/

RUN chown -R appuser:appuser /app /home/appuser/.local
USER appuser

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
