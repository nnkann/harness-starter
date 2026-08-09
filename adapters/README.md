# Adapters

Project-facing adapters belong here. They may call the isolated `harness-runtime` API, but they must not import Hermes core, open a live gateway, or use `.harness/project/runs/` as state.

`hermes_scheduled_consumer_provisioner.py` converts a validated, secret-free scheduled read-only declaration into fake-injectable `hermes cron create/edit` argv. It updates only by a receipt's exact job ID and never executes Hermes itself. `scheduled_readonly_consumer_adapter.py` is the sole boundary that accepts injected fixture values; the child environment contains exactly `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
