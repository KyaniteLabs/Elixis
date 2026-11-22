"""Deployment script safety contracts."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_local_deploy_forces_loaded_local_image_over_persisted_env():
    script = (REPO_ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")

    assert 'LOCAL_DEPLOY_IMAGE="elixis:latest"' in script
    assert "ELIXIS_IMAGE='${LOCAL_DEPLOY_IMAGE}' docker compose up" in script
    assert 'actual_image="\\$(docker inspect elixis' in script


def test_ci_deploy_uses_self_hosted_runner():
    """Deploy job uses self-hosted runner on NuC with direct SSH."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    # Deploy uses self-hosted nuc runner (which has direct SSH access to VPS)
    assert "runs-on: [self-hosted, nuc]" in workflow

    # No Tailscale action needed - runner is already in tailnet
    assert "tailscale/github-action@v4" not in workflow

    # No id-token permission needed without Tailscale
    assert "id-token" not in workflow

    # Deploy is explicitly opt-in and fail-closed: push event on a release
    # branch AND the ENABLE_VPS_DEPLOY repository variable must be "true";
    # an unset variable skips the job instead of deploying.
    assert "github.event_name == 'push'" in workflow
    assert "vars.ENABLE_VPS_DEPLOY == 'true'" in workflow

    # No hardcoded fallback VPS address: secrets.VPS_HOST is required.
    assert re.search(r"100\.\d+\.\d+\.\d+", workflow) is None
    assert "secrets.VPS_HOST ||" not in workflow

    # Host keys are pinned to secrets.VPS_SSH_KNOWN_HOSTS and verified
    # strictly; an unknown host key fails the deploy.
    assert "StrictHostKeyChecking=yes" in workflow
    assert "StrictHostKeyChecking=no" not in workflow
    assert "UserKnownHostsFile" in workflow

    # Registry credentials are ephemeral on the VPS: DOCKER_CONFIG is a
    # temp dir removed by the EXIT trap, so nothing is persisted there.
    assert "DOCKER_CONFIG" in workflow

    # No global prune on the shared VPS: sibling containers/images are out
    # of this deploy's blast radius.
    assert "docker system prune" not in workflow

    # Deploy directly via SSH as root
    assert "root@${VPS_HOST}" in workflow


def test_deploy_docs_describe_vps_target():
    docs = (REPO_ROOT / "DEPLOY.md").read_text(encoding="utf-8")

    assert "VPS_HOST=<tailscale-vps-ip>" in docs
    assert re.search(r"100\.\d+\.\d+\.\d+", docs) is None
    assert "Tailscale address" in docs
