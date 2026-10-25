SHELL := /bin/bash
PROJECT_DIR := $(shell pwd)
TOOLS_DIR := $(PROJECT_DIR)/../../tools

.PHONY: up down test audit verify status check

up:
	docker compose -f deploy/docker-compose.yml up -d

down:
	docker compose -f deploy/docker-compose.yml down

test:
	pytest backend/tests/ -v

audit:
	python3 $(TOOLS_DIR)/audit_fakes.py --project .

verify:
	python3 $(TOOLS_DIR)/check_integrity.py --project .

status:
	python3 $(TOOLS_DIR)/progress.py status --project .

check:
	python3 $(TOOLS_DIR)/progress.py check --project .
