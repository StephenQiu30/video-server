# Provider Runtime Third-Party Notices

This file covers the optional media-provider runtime components pinned by
`provider-sbom.json`. It is not a substitute for the license files shipped by
the corresponding Python packages or OCI images.

| Component | Fixed version/reference | License | Upstream source |
| --- | --- | --- | --- |
| yt-dlp | package `2026.7.4`, commit `5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc` | Unlicense; bundled dependencies retain their own notices | <https://github.com/yt-dlp/yt-dlp> |
| yt-dlp-ejs | `0.8.0` | Unlicense AND MIT AND ISC | <https://github.com/yt-dlp/ejs> |
| curl-cffi | `0.15.0` | MIT | <https://github.com/lexiforest/curl_cffi> |
| bgutil-ytdlp-pot-provider Python plugin | `1.3.1` | GPL-3.0-only | <https://github.com/Brainicism/bgutil-ytdlp-pot-provider> |
| bgutil-ytdlp-pot-provider OCI sidecar | `1.3.1`, digest `sha256:1aaa43a0ca72dfca6a6d2129a0fb4a23465c25adb1b043f8aff829a20825646b` | GPL-3.0-only; image dependencies retain their own notices | <https://github.com/Brainicism/bgutil-ytdlp-pot-provider> |
| video-server trusted extractor plugins | repository version `0.1.0` | MIT (this repository) | `app/runner/plugins/yt_dlp_plugins/` |

MeTube, cobalt and gallery-dl are research references only and are not copied,
vendored, imported or included in the Phase 1 runtime image.
