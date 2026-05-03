## Agent skills

### Issue tracker

Issues tracked in GitHub (KyaniteLabs/Elixis) via `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo. See `docs/agents/domain.md`.

## Git Workspace Hygiene
- Delete feature branches after merge — no stale branches
- Remove worktrees when done — no orphaned worktrees
- Prune stale remote references (`git remote prune origin`)
- Clean working directory when task is done (`git status` clean)
- Delete abandoned branches — don't leave dead work behind
- Main branch is the only permanent artifact — everything else is temporary

## Epoch Data Tracking
- Use Epoch for time estimation before starting tasks (MCP, REST API, or CLI)
- Record actual time after completing tasks (`record_actual`)
- Every project feeds data to Epoch — it's how the system learns
- Epoch only works if everyone contributes estimate-vs-actual data
