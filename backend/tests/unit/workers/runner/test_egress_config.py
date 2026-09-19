from pathlib import Path

import yaml

BACKEND_ROOT = Path(__file__).resolve().parents[4]
REPOSITORY_ROOT = BACKEND_ROOT.parent


def test_backend_egress_directory_and_extra_dockerfiles_are_cleaned_up() -> None:
    legacy_dir = BACKEND_ROOT / "egress"
    assert not legacy_dir.exists(), f"Legacy directory {legacy_dir} should be deleted"

    top_level_docker = REPOSITORY_ROOT / "docker"
    assert not top_level_docker.exists(), f"Top-level {top_level_docker} should not exist"

    extra_dockerfile = BACKEND_ROOT / "Dockerfile.egress"
    assert not extra_dockerfile.exists(), f"Extra Dockerfile {extra_dockerfile} should not exist"


def test_smokescreen_is_integrated_as_dockerfile_target() -> None:
    dockerfile = BACKEND_ROOT / "Dockerfile"
    assert dockerfile.exists()
    dockerfile_content = dockerfile.read_text(encoding="utf-8")
    assert "AS egress-proxy-builder" in dockerfile_content
    assert "AS egress-proxy" in dockerfile_content
    assert "ENTRYPOINT [\"smokescreen\"]" in dockerfile_content
    assert "AS runtime" in dockerfile_content


def test_compose_configures_smokescreen_environment_policies() -> None:
    dev_compose = yaml.safe_load((REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    prod_compose = yaml.safe_load((REPOSITORY_ROOT / "docker-compose-prod.yml").read_text(encoding="utf-8"))

    dev_proxy = dev_compose["services"]["egress-proxy"]
    prod_proxy = prod_compose["services"]["egress-proxy"]

    # Both environments connect to required networks
    for proxy in (dev_proxy, prod_proxy):
        assert set(proxy["networks"]) == {"runner_egress_net", "youtube_pot_net", "proxy_uplink_net"}
        assert proxy["build"]["context"] == "./backend"
        assert proxy["build"]["dockerfile"] == "Dockerfile"
        assert proxy["build"]["target"] == "egress-proxy"
        assert proxy["restart"] == "unless-stopped"
        assert proxy["stop_grace_period"] == "35s"

    # Development allows Docker Desktop synthetic DNS (198.18.0.0/15)
    dev_cmd = dev_proxy["command"]
    assert "--listen-ip=0.0.0.0" in dev_cmd
    assert "--listen-port=3128" in dev_cmd
    assert "--allow-range=198.18.0.0/15" in dev_cmd

    # Production enforces strict mode without synthetic DNS exception
    prod_cmd = prod_proxy["command"]
    assert "--listen-ip=0.0.0.0" in prod_cmd
    assert "--listen-port=3128" in prod_cmd
    assert "--allow-range=198.18.0.0/15" not in prod_cmd


def test_compose_healthcheck_uses_port_probe() -> None:
    for filename in ("docker-compose.yml", "docker-compose-prod.yml"):
        compose = yaml.safe_load((REPOSITORY_ROOT / filename).read_text(encoding="utf-8"))
        healthcheck = compose["services"]["egress-proxy"]["healthcheck"]
        assert healthcheck["test"] == ["CMD", "nc", "-z", "127.0.0.1", "3128"]
