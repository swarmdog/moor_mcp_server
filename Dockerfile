# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV MCP_HOST=0.0.0.0 \
    MCP_PORT=8085

EXPOSE 8085

ENTRYPOINT ["python", "-m", "main"]
CMD ["run"]
