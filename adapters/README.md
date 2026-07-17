# Adapters

Project-facing adapters belong here. They may call the isolated `harness-runtime` API, but they must not import Hermes core, open a live gateway, or use `.harness/project/runs/` as state.
