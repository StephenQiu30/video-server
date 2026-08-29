# Provider Runtime Third-Party Notices

This file covers the optional media-provider runtime components pinned by
`provider-sbom.json`. It is not a substitute for the license files shipped by
the corresponding Python packages or OCI images.

| Component | Fixed version/reference | License | Upstream source |
| --- | --- | --- | --- |
| yt-dlp | package `2026.8.19` (CLI `2026.08.19`), commit `3a08beaf031ab68f966401ead017ac81fe8486cf` | Unlicense; bundled dependencies retain their own notices | <https://github.com/yt-dlp/yt-dlp> |
| yt-dlp-ejs | `0.8.0` | Unlicense AND MIT AND ISC | <https://github.com/yt-dlp/ejs> |
| curl-cffi | `0.15.0` | MIT | <https://github.com/lexiforest/curl_cffi> |
| bgutil-ytdlp-pot-provider Python plugin | `1.3.2` | GPL-3.0-only | <https://github.com/Brainicism/bgutil-ytdlp-pot-provider> |
| bgutil-ytdlp-pot-provider OCI sidecar | `1.3.2`, digest `sha256:9a96e6385ce1928da87dea07b1cab0413d2cf8c07a3b8a8bd419f53df2c3843c` | GPL-3.0-only; image dependencies retain their own notices | <https://github.com/Brainicism/bgutil-ytdlp-pot-provider> |
| video-server trusted extractor plugins | repository version `0.1.0` | MIT (this repository) | `app/runner/plugins/yt_dlp_plugins/` |

MeTube, cobalt and gallery-dl are research references only and are not copied,
vendored, imported or included in the Phase 1 runtime image.
