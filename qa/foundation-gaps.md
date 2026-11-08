# Foundation evidence and remaining gaps

Baseline: `3dfda51` on `main`. Host execution: Python 3.12.3, pytest 7.4.4.
Commands below are run from the repository root with a deliberately closed local
LLM endpoint, not production inference. Provider-failure warnings and the mocked
MCP `RuntimeError: boom` traceback are expected negative-control output.

| Instrument | Executed result | Limit |
|---|---|---|
| `LLM_PROVIDER=ollama LLM_BASE_URL=http://127.0.0.1:9 python3 -m unittest discover -s tests` (baseline) | 358 passed | fallback/mocked providers, not model quality |
| `python3 -m unittest tests.test_mock_pipeline tests.test_http_server tests.test_engine tests.test_deploy_script tests.test_repo_health_workflow` | 60 passed | HTTP handlers use fake sockets |
| `python3 -m unittest tests.test_architecture_paths` | RED: missing inventory; then PASS with inventory | exact identity, schema keys, owners, nonempty pattern matches and source coverage; not gate adoption |
| `LLM_PROVIDER=ollama LLM_BASE_URL=http://127.0.0.1:9 python3 -m unittest tests.test_http_e2e -v` | 3 passed | real loopback HTTP; explicit fixture replaces synthesis backend |
| Final `LLM_PROVIDER=ollama LLM_BASE_URL=http://127.0.0.1:9 python3 -m unittest discover -s tests` | 362 passed | excludes pytest function-style tests |
| Final `python3 -m pytest tests/ -q` | 862 passed | conftest pins the dead local provider; broader collection than unittest |

## Remediation in this PR

- Root architecture and source-matched owner inventory; unittest discovery in both
  forge workflows automatically includes inventory and HTTP boundary tests.
- Real socket checks: unauthorized diagnostics is 401, invalid lens is 400 without
  invoking synthesis, valid game POST round-trips the explicit fixture with 200.
- `.forgejo/workflows/ci.yml`: replace conditional `pytest || true` with
  unconditional pytest, pinning a dead inference endpoint. Test failures
  now propagate instead of reporting success. Pytest retains function-style
  tests that unittest does not collect. Existing install/lint tolerance is
  **not** presented as a passing dependency/lint gate.

## Still open — not exclusions or adoption

1. **Engineering/Security:** open GitHub PR #156 already owns separating deploy
   from PR-triggered CI. Do not overwrite its workflow changes. Current default
   `.github/workflows/ci.yml` mixes PR tests/builds and self-hosted deployment;
   permissions/runner/environment settings and production SSH trust need their
   own approved review. No deployment, settings, release or runtime change here.
2. **Engineering:** Forgejo install and lint steps remain tolerant; packaging,
   lint and container-build execution were not established by stdlib tests.
   Browser interactions, SSE over a real socket, live-provider quality, container
   deployment and restore against real operator data are not proved by this PR.
3. **Platform:** authorized Elixis mirror mapping/default SHA/visibility is not
   supplied on the gate card at inspection time. Mirror existence, sync and hosted
   execution remain **unknown**, not reconciled success. The checked-in Forgejo
   workflow is source evidence only. No Forgejo credential attempt or bypass.
4. **Product then Security:** approve public descriptions, review exposure,
   secrets, blast radius and rollback; check the PR's exact-head hosted CI and
   merge only through Security. Local PASS is not a hosted CI verdict.
5. **Engineering/Platform:** protected-base inventory adoption and FL4WRITE
   receipt/policy integration remain under the org-wide root `t_2210091a` and
   gate program. This inventory is not a head-controlled policy waiver. No
   separate merge-gates policy added; all-estate automatic adoption stays
   disabled/ineligible until every surface is reconciled.

Risk: **6/10** (CI test-failure behavior changes on future mirror execution).
Exposure: tests bind loopback ephemeral ports only; no new service or credential.
Blast radius: repository documentation, inventory, tests and mirror test step.
Rollback: revert this PR's commit; no migration or persisted production state.
