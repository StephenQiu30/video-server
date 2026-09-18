"""Application-owned identifiers shared by persistence and message boundaries."""

from enum import StrEnum


class UrlEncryptionKeyId(StrEnum):
    """Key labels written to encrypted URL and provider-secret records."""

    FERNET = "fernet"
    LEGACY_FERNET = "fernet-v1"


class RightsStatementVersion(StrEnum):
    CONTENT = "content-rights"
    SCREENPLAY = "rights"


class SourceDiscoveryAdapter(StrEnum):
    WECHAT_ARTICLE = "wechat-article-static"


class AnalysisReportRenderer(StrEnum):
    DEFAULT = "analysis-report"


class AnalysisStorageProbe(StrEnum):
    READINESS = "system/analysis-readiness"
