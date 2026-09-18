"""Turn recognized restrictions into inspectable, non-downloadable results."""

from __future__ import annotations

import hashlib
from urllib.parse import urlsplit

from app.services.downloads.rules.content_restrictions import ContentRestriction
from app.services.downloads.rules.inspection import (
    AccessDecision,
    EntitlementState,
    ExecutionMode,
    IdentityState,
    ProtectionState,
    SourceOrigin,
)
from app.services.downloads.source_admission import RestrictedSourceAdmission

_ACTIONS = {
    ContentRestriction.PREVIEW_ONLY: (
        "平台当前仅提供试看内容，不能作为完整视频下载。"
        "请前往官方平台观看，或上传你有权使用的完整文件。"
    ),
    ContentRestriction.SUPPORTER_ONLY: (
        "这是充电专属内容，当前不支持直接下载。"
        "充电或会员观看权益不等于文件导出授权；"
        "可上传你有权使用的完整文件。"
    ),
    ContentRestriction.PAID_ONLY: (
        "这是付费内容，当前不支持直接下载。"
        "请通过官方渠道观看，或上传你有权使用的完整文件。"
    ),
    ContentRestriction.EXPORT_REQUIRED: (
        "平台返回了已购买标记，但未提供本产品可验证的文件导出授权。"
        "当前不支持直接下载，可上传你有权使用的完整文件。"
    ),
    ContentRestriction.METADATA_INVALID: (
        "平台的内容权益字段无法识别，已停止下载以避免交付试看或受限内容。"
        "请稍后重试，或上传你有权使用的完整文件。"
    ),
}


def paid_content_admission(
    url: str, reason: ContentRestriction
) -> RestrictedSourceAdmission:
    host = (urlsplit(url).hostname or "").casefold()
    provider, title = "other", "受限媒体内容"
    for domains, key, name in (
        (("bilibili.com", "b23.tv"), "bilibili", "哔哩哔哩内容"),
        (("douyin.com", "iesdouyin.com"), "douyin", "抖音内容"),
        (("youku.com",), "youku", "优酷内容"),
        (("v.qq.com",), "qqvideo", "腾讯视频内容"),
    ):
        if any(host == domain or host.endswith(f".{domain}") for domain in domains):
            provider, title = key, name
            break
    return RestrictedSourceAdmission(
        provider_key=provider,
        provider_media_id=f"source-{hashlib.sha256(url.encode()).hexdigest()[:24]}",
        title=title,
        source_origin=SourceOrigin.PUBLIC_URL,
        execution_mode=ExecutionMode.PROVIDER_RUNNER,
        access_decision=AccessDecision.BLOCKED,
        entitlement_state=(
            EntitlementState.UNKNOWN
            if reason is ContentRestriction.METADATA_INVALID
            else EntitlementState.RESTRICTED
        ),
        identity_state=IdentityState.UNKNOWN,
        protection_state=ProtectionState.UNKNOWN,
        rights_basis=None,
        restriction_reason=reason.value,
        user_action=_ACTIONS[reason],
    )
