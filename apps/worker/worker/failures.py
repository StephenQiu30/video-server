from typing import NoReturn

from app.utils.sanitize import redact_url
from worker.domain import FailureInfo, WorkerFailureCode, WorkerStage


class JobFailure(RuntimeError):
    def __init__(self, code: str | WorkerFailureCode, message: str):
        self.code = str(code)
        super().__init__(message)


def raise_task_canceled() -> NoReturn:
    raise JobFailure(WorkerFailureCode.TASK_CANCELED, "任务已取消")


def failure_code(exc: Exception) -> WorkerFailureCode:
    if isinstance(exc, JobFailure):
        try:
            return WorkerFailureCode(exc.code)
        except ValueError:
            return WorkerFailureCode.DOWNLOAD_FAILED
    message = str(exc).lower()
    if "requested format is not available" in message or "format is not available" in message:
        return WorkerFailureCode.FORMAT_UNAVAILABLE
    if "file is larger than max-filesize" in message or "larger than max-filesize" in message:
        return WorkerFailureCode.FILE_TOO_LARGE
    if "timed out" in message or "timeout" in message:
        return WorkerFailureCode.TASK_TIMEOUT
    if "unsupported url" in message or "no video formats found" in message:
        return WorkerFailureCode.UNSUPPORTED_PLATFORM
    if _looks_like_browser_cookie_error(message):
        return WorkerFailureCode.BROWSER_COOKIES_UNAVAILABLE
    return WorkerFailureCode.DOWNLOAD_FAILED


def format_failure_reason(exc: Exception) -> str:
    if isinstance(exc, JobFailure) and exc.code == WorkerFailureCode.TASK_CANCELED:
        return "任务已取消"
    lowered = str(exc).lower()
    if _looks_like_browser_cookie_error(lowered):
        return (
            "无法读取本机 Chrome 登录态。请确认 Chrome 已登录 B 站，并允许当前终端或 Python 访问浏览器数据；"
            "如果只下载公开视频，也可以关闭 YTDLP_COOKIES_FROM_BROWSER 后重试。"
        )
    if "requested format is not available" in lowered or "format is not available" in lowered:
        return "该视频源未提供所选清晰度，请选择推荐下载或其他可用清晰度后重试。"
    if "unsupported url" in lowered or "no video formats found" in lowered:
        return "该公开视频暂不支持解析或平台规则已变化，请换用公开视频链接后重试。"
    message = str(exc).strip().splitlines()[0] if str(exc).strip() else "下载任务失败"
    if message.startswith("ERROR: "):
        message = message[len("ERROR: ") :]
    return redact_url(message)[:300]


def failure_info_from_exception(exc: Exception, stage: WorkerStage) -> FailureInfo:
    code = failure_code(exc)
    return FailureInfo(
        code=code,
        reason=format_failure_reason(exc),
        stage=stage,
        retryable=code
        in {
            WorkerFailureCode.DOWNLOAD_FAILED,
            WorkerFailureCode.STORAGE_FAILED,
            WorkerFailureCode.TASK_TIMEOUT,
            WorkerFailureCode.PLATFORM_RATE_LIMITED,
        },
    )


def _looks_like_browser_cookie_error(message: str) -> bool:
    needles = (
        "cookies",
        "cookie",
        "cookiesfrombrowser",
        "keyring",
        "keychain",
        "browser",
        "chrome",
        "chromium",
    )
    return any(needle in message for needle in needles)
