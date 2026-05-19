"""Deployment script safety contracts."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_local_deploy_forces_loaded_local_image_over_persisted_env():
    script = (REPO_ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")

    assert 'LOCAL_DEPLOY_IMAGE="elixis:latest"' in script
    assert "ELIXIS_IMAGE='${LOCAL_DEPLOY_IMAGE}' docker compose up" in script
    assert 'actual_image="\\$(docker inspect elixis' in script
