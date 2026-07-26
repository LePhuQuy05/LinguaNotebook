.PHONY: dev stop test lint typecheck build seed clean

dev:
	docker compose -f docker/docker-compose.yml up -d
	@echo "Backend:  http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "Qdrant:   http://localhost:6333"
	@echo "MinIO:    http://localhost:9001"

stop:
	docker compose -f docker/docker-compose.yml down

test:
	cd backend && pytest
	cd frontend && pnpm test
	cd mobile && pnpm test

lint:
	cd backend && ruff check src/ tests/
	cd frontend && pnpm lint
	cd mobile && pnpm lint

typecheck:
	cd backend && mypy src/ --strict
	cd frontend && pnpm typecheck
	cd shared && pnpm typecheck

build:
	cd shared && pnpm build
	cd frontend && pnpm build

seed:
	docker compose exec backend-api python scripts/seed.py

clean:
	docker compose -f docker/docker-compose.yml down -v
	rm -rf frontend/.next frontend/node_modules
	rm -rf mobile/node_modules
	rm -rf shared/dist shared/node_modules
	rm -rf backend/__pycache__ backend/.pytest_cache
