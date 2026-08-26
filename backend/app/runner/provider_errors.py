"""Ordered, data-driven yt-dlp failure classification rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderFailureContext:
    provider_key: str
    source_url: str
    authenticated: bool


@dataclass(frozen=True, slots=True)
class FailureRule:
    code: str
    status: int
    any_stderr: tuple[bytes, ...] = ()
    all_stderr: tuple[bytes, ...] = ()
    providers: frozenset[str] = frozenset()
    any_url: tuple[str, ...] = ()
    authenticated: bool | None = None

    def matches(self, context: ProviderFailureContext, stderr: bytes) -> bool:
        source_url = context.source_url.casefold()
        return (
            (not self.providers or context.provider_key in self.providers)
            and (not self.any_url or any(value in source_url for value in self.any_url))
            and (
                self.authenticated is None
                or context.authenticated is self.authenticated
            )
            and (
                not self.any_stderr
                or any(marker in stderr for marker in self.any_stderr)
            )
            and all(marker in stderr for marker in self.all_stderr)
        )


PROVIDER_FAILURE_RULES: tuple[FailureRule, ...] = (
    FailureRule(
        "provider_unsupported",
        422,
        any_stderr=(b"unsupported url:",),
        any_url=("channels.weixin.qq.com", "weixin.qq.com/sph/"),
    ),
    FailureRule(
        "provider_unsupported",
        422,
        any_stderr=(
            b"kuaishou image posts are not supported by the video runner",
        ),
        providers=frozenset({"kuaishou"}),
    ),
    FailureRule(
        "provider_media_unsupported",
        422,
        any_stderr=(
            b"facebook image and multi-asset posts are not supported",
        ),
        providers=frozenset({"facebook"}),
    ),
    FailureRule(
        "provider_link_unavailable",
        422,
        any_stderr=(
            b"video unavailable",
            b"this video is unavailable",
            b"video is no longer available",
        ),
        providers=frozenset({"youtube"}),
    ),
    FailureRule(
        "provider_link_unavailable",
        422,
        any_stderr=(
            b"unsupported url:",
            b"unable to extract initial state",
            b"kuaishou public link unavailable",
        ),
        providers=frozenset({"douyin", "xiaohongshu", "kuaishou"}),
    ),
    FailureRule(
        "drm_protected",
        422,
        any_stderr=(
            b"only drm protected formats",
            b"this video is drm protected",
            b"this format is drm protected",
        ),
    ),
    FailureRule(
        "content_private",
        403,
        any_stderr=(b"private video", b"this video is private"),
    ),
    FailureRule(
        "content_not_entitled",
        403,
        any_stderr=(
            b"members-only content",
            b"join this channel",
            b"premium-only",
            b"subscriber-only",
            b"not entitled",
        ),
    ),
    FailureRule(
        "credential_expired",
        422,
        any_stderr=(
            b"account cookies are no longer valid",
            b"cookies have been rotated",
            b"cookie is no longer valid",
        ),
    ),
    FailureRule(
        "credential_expired",
        422,
        all_stderr=(b"sign in to confirm", b"not a bot"),
        authenticated=True,
    ),
    FailureRule(
        "egress_challenged",
        422,
        all_stderr=(b"sign in to confirm", b"not a bot"),
        authenticated=False,
    ),
    FailureRule(
        "provider_rate_limited",
        429,
        any_stderr=(b"http error 429", b"too many requests", b"rate limit exceeded"),
    ),
    FailureRule(
        "provider_geo_restricted",
        422,
        any_stderr=(
            b"not available in your country",
            b"not available in your region",
            b"geo restricted",
        ),
    ),
    FailureRule(
        "pot_provider_unavailable",
        503,
        any_stderr=(b"provider unavailable", b"provider failed", b"timed out"),
        all_stderr=(b"po token",),
    ),
    FailureRule(
        "pot_rejected",
        422,
        any_stderr=(b"invalid", b"rejected", b"http error 403"),
        all_stderr=(b"po token",),
    ),
    FailureRule(
        "pot_required",
        422,
        any_stderr=(b"required", b"was not provided", b"missing"),
        all_stderr=(b"po token",),
    ),
    FailureRule(
        "credential_required",
        422,
        all_stderr=(b"fresh cookies", b"needed"),
    ),
    FailureRule(
        "credential_required",
        422,
        any_stderr=(
            b"vimeo extractor only works when logged-in",
            b"account authentication is required",
            b"rate-limit reached or login required",
            b"login required. use --cookies",
        ),
    ),
    FailureRule(
        "egress_challenged",
        422,
        any_stderr=(
            b"unexpected response from webpage request",
            b"unable to extract challenge data",
            b"unable to extract universal data for rehydration",
        ),
        providers=frozenset({"tiktok"}),
    ),
    FailureRule(
        "extractor_regression",
        502,
        any_stderr=(
            b"cannot parse data",
            b"facebook post media structure could not be identified",
        ),
        providers=frozenset({"facebook"}),
    ),
    FailureRule(
        "extractor_regression",
        502,
        any_stderr=(
            b"no video formats found",
            b"xiaohongshu note media structure could not be identified",
        ),
        providers=frozenset({"xiaohongshu"}),
    ),
    FailureRule(
        "extractor_regression",
        502,
        any_stderr=(
            b"unable to extract",
            b"expected one video in the playlist",
            b"unexpected response from webpage request",
            b"universal data for rehydration",
        ),
    ),
)


def classify_provider_failure(
    context: ProviderFailureContext,
    stderr: bytes,
) -> tuple[str, int] | None:
    normalized = stderr.lower()
    for rule in PROVIDER_FAILURE_RULES:
        if rule.matches(context, normalized):
            return rule.code, rule.status
    return None
