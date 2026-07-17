# Harness Hermes USER Template

This file is a template for profile-local user memory. Local Hermes profile
homes own the actual `USER.md`; this adapter export only records allowed shape.

## Memory Separation

- User preferences belong in `USER.md`.
- Agent identity and hard rules belong in `SOUL.md`.
- Project rules belong in the project `AGENTS.md` or the harness rule pack.
- Task facts belong in Kanban comments, task packets, or repo evidence.
- Long-term profile memory must not store full CPS bodies, secrets, tokens,
  claim locks, webhook data, or copied task databases.

## Safe Preference Examples

- Preferred language and tone.
- Reporting format preferences.
- Known owner-action sensitivity.
- Project naming preferences.
- Review strictness preferences.

## Forbidden Memory

- Secrets, tokens, private webhook URLs, or credentials.
- Raw `HERMES_KANBAN_DB` contents.
- `HERMES_KANBAN_CLAIM_LOCK` values.
- Cross-project task details that are not explicitly part of the current board.
- Filesystem paths as write authority.

## Project Isolation

When a shared profile serves multiple boards, user memory may contain thin
project pointers and outcome summaries only. It must not become a hidden source
of board, workspace, gateway, or filesystem permission.
