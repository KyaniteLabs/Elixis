from pathlib import Path


WORKFLOW = Path(".github/workflows/repo-health.yml")


def test_repo_health_workflow_authenticates_github_cli() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "actions: read" in workflow
    assert "GH_TOKEN: ${{ github.token }}" in workflow
