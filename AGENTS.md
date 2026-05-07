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

<!-- EMPOWER_ORCHESTRATOR:START -->
## Empower the Orchestrator

This repository is governed by the Empower Orchestrator law. Every top-level/orchestrator agent session is an audition to improve the system, not only finish the current task.

When you notice a repeatable task done 3+ times or a recurring agent failure mode, consider shipping the smallest durable artifact that prevents the repetition: a tool, skill, slash command, hook, guardrail, memory entry, test, verifier, or doctrine doc.

This applies to top-level/orchestrator sessions. Background workers execute their assigned slice and do not independently widen scope.

Before dispatching automation or creating a durable system change, state the four-question blast-radius check in chat:

1. Scale: one file/workspace/all sessions?
2. Severity: minor friction/broken workflow/data loss or leaked content?
3. Reversibility: single revert/manual cleanup/surgery?
4. Predictability: bounded failure mode/guessing/unknown?

All green permits auto mode. Any yellow requires inline human approval. Any red means do not dispatch; do the work inline or escalate.

Worker discipline: isolated worktree/sandbox, one artifact equals one commit/change unit, verify before commit, register through the target tool's native discovery surface, and never write outside the assigned scope.

Success line: “I noticed X, found a better way. The system just got an upgrade.”

Full recipe: `docs/agent-law/empower-orchestrator.md`.
<!-- EMPOWER_ORCHESTRATOR:END -->
