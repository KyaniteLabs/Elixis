"""Deployment script safety contracts."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_local_deploy_forces_loaded_local_image_over_persisted_env():
    script = (REPO_ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")

    assert 'LOCAL_DEPLOY_IMAGE="elixis:latest"' in script
    assert "ELIXIS_IMAGE='${LOCAL_DEPLOY_IMAGE}' docker compose up" in script
    assert 'actual_image="\\$(docker inspect elixis' in script


def test_ci_deploy_uses_tailscale_before_ssh():
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "id-token: write" in workflow
    assert "tailscale/github-action@v4" in workflow
    assert "VPS_HOST must be a Tailscale address or MagicDNS name" in workflow
    assert "Public SSH deploy is not allowed" in workflow
    assert "TS_OAUTH_CLIENT_ID" in workflow
    assert "TS_AUDIENCE" in workflow
    assert "TS_OAUTH_SECRET" in workflow
    assert "TAILSCALE_AUTHKEY" in workflow
    assert workflow.index("tailscale/github-action@v4") < workflow.index("Deploy to VPS")


def test_deploy_docs_require_tailnet_target():
    docs = (REPO_ROOT / "DEPLOY.md").read_text(encoding="utf-8")

    assert "VPS_HOST=100.92.68.103" in docs
    assert "must be the Tailscale address or MagicDNS name" in docs
    assert "not allowed to silently skip production deployment or open public SSH" in docs
