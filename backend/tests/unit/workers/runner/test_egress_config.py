from pathlib import Path

import yaml

BACKEND_ROOT = Path(__file__).resolve().parents[4]
CONFIG = BACKEND_ROOT / "egress" / "squid.conf"
CONFIG_ROOT = CONFIG.parent
REPOSITORY_ROOT = BACKEND_ROOT.parent
SQUID_IMAGE = (
    "ubuntu/squid:6.6-24.04_edge@"
    "sha256:8a3baed477e2c282ab8aa5edad442f69873246964f225c5c2ae8364b6610963c"
)
EXPECTED_TMPFS = ["/tmp:rw,noexec,nosuid,size=16m,mode=1777"]


def load_compose(filename: str) -> dict:
    return yaml.safe_load((REPOSITORY_ROOT / filename).read_text(encoding="utf-8"))


def test_bilibili_tls_media_port_is_scoped_to_its_cdn() -> None:
    config = CONFIG.read_text(encoding="utf-8")

    assert "acl safe_ports port 4483" in config
    assert "acl safe_ports port 8082" in config
    assert "acl ssl_ports port 4483" in config
    assert "acl ssl_ports port 8082" in config
    assert (
        "acl bilibili_media dstdom_regex -i "
        "\\.(bilivideo\\.(cn|com)|mountaintoys\\.cn)$" in config
    )
    assert "http_access deny bilibili_media_port !bilibili_media" in config
    assert (
        "http_access allow docker_clients bilibili_media_port "
        "bilibili_media docker_desktop_public" in config
    )
    assert "acl docker_desktop_web_port port 80 443" in config
    assert (
        "http_access allow docker_clients docker_desktop_web_port "
        "docker_desktop_public" in config
    )

    scoped_deny = config.index("http_access deny bilibili_media_port !bilibili_media")
    public_allow = config.index("http_access allow docker_clients")
    assert scoped_deny < public_allow


def test_destination_policies_separate_linux_and_docker_desktop_dns() -> None:
    production = (CONFIG_ROOT / "blocked-destinations.conf").read_text(encoding="utf-8")
    docker_desktop = (
        CONFIG_ROOT / "blocked-destinations-docker-desktop.conf"
    ).read_text(encoding="utf-8")

    assert "acl docker_desktop_public dst 255.255.255.255/32" in production
    assert "acl blocked_destination dst 198.18.0.0/15" in production
    assert "acl docker_desktop_public dst 198.18.0.0/15" in docker_desktop
    assert "acl blocked_destination dst 198.18.0.0/15" not in docker_desktop


def test_compose_selects_environment_specific_destination_policy() -> None:
    development = load_compose("docker-compose.yml")
    production = load_compose("docker-compose-prod.yml")

    variable = "EGRESS_DESTINATION_POLICY_FILE"
    assert variable in (REPOSITORY_ROOT / "docker-compose.yml").read_text(
        encoding="utf-8"
    )
    assert variable in (REPOSITORY_ROOT / "docker-compose-prod.yml").read_text(
        encoding="utf-8"
    )
    assert "blocked-destinations-docker-desktop.conf" in str(development)
    assert "blocked-destinations.conf" in str(production)

    development_example = (REPOSITORY_ROOT / ".env.example").read_text(encoding="utf-8")
    assert (
        f"{variable}=./backend/egress/blocked-destinations-docker-desktop.conf"
        in development_example
    )
    assert "${" + variable + ":-./backend/egress/blocked-destinations.conf}" in (
        REPOSITORY_ROOT / "docker-compose-prod.yml"
    ).read_text(encoding="utf-8")


def test_egress_proxy_uses_pinned_squid_without_a_go_build_surface() -> None:
    dockerfile = (BACKEND_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert not (BACKEND_ROOT / "egress-proxy").exists()
    assert "golang" not in dockerfile
    assert "smokescreen" not in dockerfile
    assert "squid" not in dockerfile

    for filename in ("docker-compose.yml", "docker-compose-prod.yml"):
        proxy = load_compose(filename)["services"]["egress-proxy"]
        assert proxy["image"] == SQUID_IMAGE
        assert "build" not in proxy
        assert proxy["entrypoint"] == ["squid"]
        assert proxy["command"] == ["-N", "-f", "/etc/squid/squid.conf"]
        assert proxy["tmpfs"] == EXPECTED_TMPFS
        assert proxy["volumes"][0] == (
            "./backend/egress/squid.conf:/etc/squid/squid.conf:ro"
        )
        assert proxy["healthcheck"]["test"] == [
            "CMD",
            "squid",
            "-k",
            "check",
            "-f",
            "/etc/squid/squid.conf",
        ]
