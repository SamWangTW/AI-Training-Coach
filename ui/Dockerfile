# ---- Stage 1: builder ----
FROM python:3.12-slim AS builder
WORKDIR /app

COPY requirements-ui.txt .
RUN pip install --user --no-cache-dir -r requirements-ui.txt

# ---- Stage 2: runtime ----
FROM python:3.12-slim
WORKDIR /app

RUN useradd --create-home appuser
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

COPY app.py .

RUN chown -R appuser:appuser /app /home/appuser/.local
USER appuser

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
