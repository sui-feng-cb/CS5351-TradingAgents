# Memory and state

Existing upstream memory, caches, SQLite checkpoints and reports are application
state, not team-authored new functionality. They default to user locations in
upstream; configure project-local paths in `.env` for actual development runs.
Keep `.env`, `.runtime/`, caches, tools and venv out of Git.

C's proposed manifests live beside run reports with versioned schema and unique
run IDs; missing information is explicit. Query must not mutate state. B keeps
only bounded per-run evidence, with no cross-run learning in this MVP. D consumes
execution metadata for the same run, rejecting mismatched/stale state.

The D implementation gives team checkpoints a different run signature from
standard checkpoints. Internal candidate PM fields can exist in the local
checkpoint until qualification; `stream_run` strips them and the gate clears
them on completion. Team `REVIEW` results retain a JSON state log with reasons
but never create a new pending memory-log entry, so that rejected call cannot
trigger later settlement/reflection. Standard-mode memory behavior is preserved.

Owner of local run data is the person executing the run; no sensitive account
inputs belong in shared fixtures. Propose local run-data retention of 30 days,
subject to human approval; retain sanitized submission evidence through marking.
Delete expired local state only after user confirmation. Resume signatures and
historical memory cutoffs preserve upstream behavior. Schema changes require a
version bump, compatibility decision and explicit unsupported-version warning.
