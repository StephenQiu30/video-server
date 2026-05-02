from enum import StrEnum


class TaskState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


ACTIVE_TASK_STATES = (TaskState.QUEUED, TaskState.RUNNING)

