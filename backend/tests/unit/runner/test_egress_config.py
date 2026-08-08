from pathlib import Path

CONFIG = Path(__file__).resolve().parents[3] / "config" / "egress" / "squid.conf"
CONFIG_ROOT = CONFIG.parent


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
