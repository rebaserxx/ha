.PHONY: sync-ha verify

sync-ha:
	./scripts/sync_from_ha.sh sync

verify:
	./scripts/sync_from_ha.sh verify
