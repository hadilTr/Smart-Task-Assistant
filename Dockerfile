FROM python:3.12-slim


LABEL maintainer="Hadil" \
    description="SmartTaskAssistant MCP Server"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_HOME=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --home-dir ${APP_HOME} --shell /bin/bash appuser
WORKDIR ${APP_HOME}

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R appuser:appuser ${APP_HOME}
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD [ "python", "-c", "import os; print('ok')" ]

ENTRYPOINT ["python", "server.py"]
