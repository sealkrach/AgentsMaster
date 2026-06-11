FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY runtime/ runtime/
COPY scripts/ scripts/
COPY mock_sources/ mock_sources/
COPY mcp_servers/ mcp_servers/
COPY skills/ skills/
COPY data/ data/
COPY ui/ ui/
COPY db/ db/
COPY connector_specs/ connector_specs/
COPY alembic/ alembic/
COPY alembic.ini .

# OpenShift : UID arbitraire, le groupe root doit pouvoir écrire.
RUN mkdir -p /app/workspace && chgrp -R 0 /app && chmod -R g=u /app
USER 1001

EXPOSE 8080
# Par défaut on lance le runtime. Les serveurs MCP utilisent la même image avec
# une commande différente (voir deploy/openshift/mcp-servers.yaml).
CMD ["uvicorn", "runtime.app:app", "--host", "0.0.0.0", "--port", "8080"]
