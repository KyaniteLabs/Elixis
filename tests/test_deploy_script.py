"""Deployment script safety contracts."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_local_deploy_forces_loaded_local_image_over_persisted_env():
    script = (REPO_ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")

    assert 'LOCAL_DEPLOY_IMAGE="elixis:latest"' in script
    assert "ELIXIS_IMAGE='${LOCAL_DEPLOY_IMAGE}' docker compose up" in script
    assert 'actual_image="\\$(docker inspect elixis' in script


def test_ci_has_no_dead_self_hosted_deploy():
    """The [self-hosted, nuc] deploy job is gone: NucBox GitHub runners are retired
    (fleet GIT-CI-STRATEGY-20261123). CI must not queue on a runner that never comes."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "self-hosted" not in workflow
    assert re.search(r"100\.\d+\.\d+\.\d+", workflow) is None


def test_deploy_docs_describe_vps_target():
    docs = (REPO_ROOT / "DEPLOY.md").read_text(encoding="utf-8")

    assert "VPS_HOST=<tailscale-vps-ip>" in docs
    assert re.search(r"100\.\d+\.\d+\.\d+", docs) is None
    assert "Tailscale address" in docs
