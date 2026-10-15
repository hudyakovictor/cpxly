# Added by Capexly. Upstream targets remain unchanged and are not the supported full-Docker path.
capexly-config: ## Added by us: validate merged Compose WITHOUT printing secrets
	@./scripts/compose.sh config --quiet
capexly-build: ## Added by us: build development containers
	@./scripts/compose.sh build
capexly-up: ## Added by us: start full container environment
	@./scripts/compose.sh up -d
capexly-down: ## Added by us: stop WITHOUT deleting volumes
	@./scripts/compose.sh down
capexly-migrate: ## Added by us: explicit migrations with dedicated role
	@./scripts/compose.sh run --rm migrate
	@./scripts/compose.sh run --rm db-ops
capexly-test: ## Added by us: tests only in prepared isolated CI database
	@./scripts/runtime-tests.sh $(ARGS)
capexly-check: ## Added by us: security checks under runtime role
	@./scripts/compose.sh run --rm web python manage.py check --deploy
capexly-release-build: ## Added by us: unique amd64 image from reviewed clean committed source
	@APP_IMAGE="$(APP_IMAGE)" ./scripts/release-build.sh
capexly-release-save: ## Added by us: archive approved images and sha256
	@./scripts/release-save.sh "$(ARCHIVE)"
capexly-release-load: ## Added by us: verify checksum BEFORE loading images
	@./scripts/release-load.sh "$(ARCHIVE)"

capexly-prod-test: ## Added by us: isolated production-like smoke, never a VPS deployment
	@./scripts/prod-test-smoke.sh
capexly-backup: ## Added by us: approved coherent DB+private-object recovery set
	@./scripts/backup-set.sh
capexly-restore-test: ## Added by us: restore ONLY into empty synthetic test environment
	@./scripts/restore-set.sh "$(BACKUP_SET)"
