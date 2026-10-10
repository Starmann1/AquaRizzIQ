# AquaRizz Local-First Development Makefile (NO DOCKER)
.PHONY: help setup install db-seed backend frontend test lint run-demo

help:
	@echo "AquaRizz Build & Run Targets (Local-First, Native Processes):"
	@echo "  make setup      - Install Python & Node dependencies"
	@echo "  make db-seed    - Seed database with wards, sensors, and sample events"
	@echo "  make backend    - Start FastAPI backend server on http://localhost:8000"
	@echo "  make frontend   - Start Vite frontend on http://localhost:5173"
	@echo "  make test       - Run backend test suite"
	@echo "  make run-demo   - Run complete end-to-end demo cycle"

setup:
	pip install -r requirements.txt
	cd apps/web && npm install

backend:
	python -m uvicorn apps.api.app.main:app --host 127.0.0.1 --port 8000 --reload

frontend:
	cd apps/web && npm run dev

test:
	pytest apps/api/tests -v

db-seed:
	python scripts/seed_data.py

run-demo:
	python scripts/run_demo.py

