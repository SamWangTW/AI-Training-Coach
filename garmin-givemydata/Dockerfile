# ---- Stage 1: builder ----
FROM python:3.12-slim AS builder
WORKDIR /app

COPY requirements-mcp-docker.txt .
RUN pip install --user --no-cache-dir -r requirements-mcp-docker.txt

# ---- Stage 2: runtime ----
FROM python:3.12-slim
WORKDIR /app

RUN useradd --create-home appuser
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

COPY garmin_mcp/ ./garmin_mcp/
COPY run_mcp.py .

# This image only ever runs as a networked service (not stdio), so bake in
# the transport + host defaults rather than relying on compose to set them.
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000
ENV GARMIN_DATA_DIR=/data

RUN mkdir -p /data && chown -R appuser:appuser /app /home/appuser/.local /data
USER appuser

EXPOSE 8000

CMD ["python", "run_mcp.py"]
