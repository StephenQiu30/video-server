"""Stable, public download-source taxonomy for administrator reporting."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DownloadSource:
    key: str
    name: str
    extractor_prefixes: tuple[str, ...]


DOWNLOAD_SOURCES: tuple[DownloadSource, ...] = (
    DownloadSource("youtube", "YouTube", ("youtube",)),
    DownloadSource("bilibili", "哔哩哔哩", ("bilibili", "biliintl")),
    DownloadSource("douyin", "抖音", ("douyin",)),
    DownloadSource("tiktok", "TikTok", ("tiktok",)),
    DownloadSource("xiaohongshu", "小红书", ("xiaohongshu",)),
    DownloadSource("kuaishou", "快手", ("kuaishou",)),
    DownloadSource("vimeo", "Vimeo", ("vimeo",)),
    DownloadSource("x", "X / Twitter", ("twitter",)),
    DownloadSource("instagram", "Instagram", ("instagram",)),
    DownloadSource("facebook", "Facebook", ("facebook",)),
    DownloadSource("twitch", "Twitch", ("twitch",)),
    DownloadSource("reddit", "Reddit", ("reddit",)),
    DownloadSource("pinterest", "Pinterest", ("pinterest",)),
    DownloadSource("weibo", "微博", ("weibo",)),
    DownloadSource("youku", "优酷", ("youku",)),
    DownloadSource(
        "qqvideo",
        "腾讯视频",
        ("vqqvideo", "qqvideo", "tencentvideo"),
    ),
    DownloadSource("mediatrack", "MediaTrack", ("mediatrack",)),
)
OTHER_DOWNLOAD_SOURCE = DownloadSource("other", "其他来源", ())
BROWSER_IMPORT_DOWNLOAD_SOURCE = DownloadSource("browser_import", "本地视频上传", ())

_SOURCES_BY_KEY = {
    source.key: source for source in (*DOWNLOAD_SOURCES, BROWSER_IMPORT_DOWNLOAD_SOURCE)
}


def download_source(key: str) -> DownloadSource:
    return _SOURCES_BY_KEY.get(key, OTHER_DOWNLOAD_SOURCE)
