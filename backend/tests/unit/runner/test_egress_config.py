from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[3]
CONFIG = BACKEND_ROOT / "egress" / "squid.conf"
CONFIG_ROOT = CONFIG.parent
REPOSITORY_ROOT = BACKEND_ROOT.parent


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


def test_docker_desktop_public_range_is_not_trusted_in_production() -> None:
    production = (CONFIG_ROOT / "blocked-destinations.conf").read_text(encoding="utf-8")
    docker_desktop = (
        CONFIG_ROOT / "blocked-destinations-docker-desktop.conf"
    ).read_text(encoding="utf-8")

    assert "acl docker_desktop_public dst 255.255.255.255/32" in production
    assert "acl blocked_destination dst 198.18.0.0/15" in production
    assert "acl docker_desktop_public dst 198.18.0.0/15" in docker_desktop
    assert "acl blocked_destination dst 198.18.0.0/15" not in docker_desktop


def test_compose_selects_environment_specific_destination_policy() -> None:
    development = (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    production = (REPOSITORY_ROOT / "docker-compose-prod.yml").read_text(
        encoding="utf-8"
    )

    assert "backend/egress/blocked-destinations-docker-desktop.conf" in development
    assert "backend/egress/blocked-destinations.conf" in production
    assert "blocked-destinations-docker-desktop.conf" not in production
