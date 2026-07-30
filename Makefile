.PHONY: dev dev-logs dev-down snapshot seed provision-roles provision-flows provision-contact-flow provision-public-read deploy-staging deploy-prod backup-staging backup-prod

dev:
	docker compose -f docker/dev/docker-compose.yml --env-file .env up -d

dev-logs:
	docker compose -f docker/dev/docker-compose.yml logs -f

dev-down:
	docker compose -f docker/dev/docker-compose.yml down

snapshot:
	./scripts/snapshot.sh

seed:
	./scripts/seed.sh

provision-roles:
	./scripts/provision_roles.sh

provision-flows:
	./scripts/provision_admissions_flow.sh

provision-contact-flow:
	./scripts/provision_contact_flow.sh

provision-public-read:
	./scripts/provision_public_read.sh

deploy-staging:
	./scripts/deploy.sh staging

deploy-prod:
	./scripts/deploy.sh prod

backup-staging:
	./scripts/backup.sh staging

backup-prod:
	./scripts/backup.sh prod
