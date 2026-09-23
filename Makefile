.PHONY: install test pentest run docker-up docker-pg certs lint

install:
	pip3 install --user -r backend/requirements.txt

test:
	cd backend && PYTHONPATH=. python3 -m pytest app/tests/ -q

pentest:
	API_URL=$${API_URL:-http://127.0.0.1:8000} bash scripts/penetration-test.sh

run:
	bash scripts/run-all-local.sh

docker-up:
	docker compose up --build -d backend frontend

docker-pg:
	docker compose --profile postgres up --build -d postgres pgadmin backend-pg frontend

certs:
	bash scripts/generate-postgres-certs.sh
	bash scripts/generate-pgadmin-certs.sh

scan:
	bash scripts/security-scan.sh
