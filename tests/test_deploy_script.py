"""Deployment script safety contracts."""

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

    # Direct SSH to VPS (hardcoded fallback to Tailscale IP)
    assert "100.92.68.103" in workflow
    assert "VPS_USER: root" in workflow

    # No id-token permission needed without Tailscale
    assert "id-token" not in workflow

    # Deploy directly via SSH
    assert "ssh -o StrictHostKeyChecking=no" in workflow
    assert "root@${VPS_HOST}" in workflow


def test_deploy_docs_describe_vps_target():
    docs = (REPO_ROOT / "DEPLOY.md").read_text(encoding="utf-8")

    assert "VPS_HOST=100.92.68.103" in docs
    assert "Tailscale address" in docs
