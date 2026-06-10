.PHONY: help install mcp up up-inproc eval new-skill gen-mcp gen-skill ns-up ns-down \
        db-up db-down db-migrate db-shell

help:
	@echo "Cibles :"
	@echo "  make install              installe les dépendances"
	@echo "  make db-up                démarre PostgreSQL+pgvector (docker-compose)"
	@echo "  make db-down              arrête PostgreSQL"
	@echo "  make db-migrate           applique les migrations Alembic"
	@echo "  make db-shell             ouvre psql dans le conteneur"
	@echo "  make mcp                  lance les 4 serveurs MCP (mode mcp)"
	@echo "  make up                   lance le runtime (http://localhost:8080)"
	@echo "  make up-inproc            lance le runtime sans serveurs MCP (fallback)"
	@echo "  make eval                 lance l'eval du skill exemple"
	@echo "  make new-skill name=xxx   crée un nouveau skill (template)"
	@echo "  make gen-skill name=xxx description=\"...\"  génère un skill complet avec l'IA"
	@echo "  make gen-mcp   name=xxx description=\"...\"  génère un serveur MCP avec l'IA"
	@echo "  make ns-up team=alpha     provisionne un namespace éphémère OpenShift"
	@echo "  make ns-down team=alpha   supprime le namespace d'une équipe"
	@echo ""
	@echo "Démarrage local avec registre :"
	@echo "  make db-up && make db-migrate  # une seule fois"
	@echo "  DATABASE_URL=postgresql+asyncpg://lab:lab@localhost:5432/agentathon make up-inproc"

install:
	pip install -r requirements.txt --break-system-packages

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

db-migrate:
	alembic upgrade head

db-shell:
	docker compose exec postgres psql -U lab -d agentathon

mcp:
	python -m mcp_servers all

up:
	uvicorn runtime.app:app --host 0.0.0.0 --port 8080

up-inproc:
	MCP_MODE=inproc uvicorn runtime.app:app --host 0.0.0.0 --port 8080

eval:
	MCP_MODE=inproc python -m eval.run_eval

new-skill:
	@test -n "$(name)" || (echo "Usage: make new-skill name=mon-skill"; exit 1)
	./scripts/new_skill.sh $(name)

gen-skill:
	@test -n "$(name)" || (echo "Usage: make gen-skill name=xxx description=\"...\""; exit 1)
	@test -n "$(description)" || (echo "Usage: make gen-skill name=xxx description=\"...\""; exit 1)
	python scripts/gen_skill.py --name $(name) --description "$(description)"

gen-mcp:
	@test -n "$(name)" || (echo "Usage: make gen-mcp name=xxx description=\"...\""; exit 1)
	@test -n "$(description)" || (echo "Usage: make gen-mcp name=xxx description=\"...\""; exit 1)
	python scripts/gen_mcp.py --name $(name) --description "$(description)"

ns-up:
	@test -n "$(team)" || (echo "Usage: make ns-up team=alpha"; exit 1)
	./scripts/provision_namespace.sh $(team)

ns-down:
	@test -n "$(team)" || (echo "Usage: make ns-down team=alpha"; exit 1)
	oc delete ns agentathon-$(team)
