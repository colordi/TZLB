from __future__ import annotations

import asyncio
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from backend.logging_config import get_logger
from backend.schemas import WorkOrderBatchGenerateRequest
from backend.services.docgen import GeneratedArtifact, generate_workorder_batch_artifact


logger = get_logger(__name__)

JOB_TTL_SECONDS = 30 * 60
JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"


@dataclass
class BatchExportJob:
    job_id: str
    status: str = JOB_STATUS_QUEUED
    current: int = 0
    total: int = 0
    percent: int = 0
    phase: str = "queued"
    message: str = "任务已创建"
    error: str | None = None
    filename: str | None = None
    media_type: str | None = None
    content: bytes | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    def to_status_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "current": self.current,
            "total": self.total,
            "percent": self.percent,
            "phase": self.phase,
            "message": self.message,
            "error": self.error,
            "filename": self.filename,
            "ready_for_download": self.status == JOB_STATUS_COMPLETED and self.content is not None,
        }


class WorkorderBatchJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, BatchExportJob] = {}
        self._lock = threading.RLock()

    def create(self, total_records: int) -> BatchExportJob:
        self.cleanup_expired()
        job = BatchExportJob(
            job_id=uuid.uuid4().hex,
            total=max(total_records + 1, 1),
            message="任务排队中",
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> BatchExportJob | None:
        self.cleanup_expired()
        with self._lock:
            return self._jobs.get(job_id)

    def update_progress(
        self,
        job_id: str,
        *,
        current: int,
        total: int,
        phase: str,
        message: str = "",
        status: str = JOB_STATUS_RUNNING,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = status
            job.current = max(0, current)
            job.total = max(total, 1)
            job.percent = min(100, int(round((job.current / job.total) * 100)))
            job.phase = phase
            if message:
                job.message = message
            job.updated_at = time.time()

    def complete(self, job_id: str, artifact: GeneratedArtifact) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = JOB_STATUS_COMPLETED
            job.current = job.total
            job.percent = 100
            job.phase = "completed"
            job.message = "导出完成，可下载"
            job.filename = artifact.filename
            job.media_type = artifact.media_type
            job.content = artifact.content
            job.error = None
            now = time.time()
            job.updated_at = now
            job.finished_at = now

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = JOB_STATUS_FAILED
            job.phase = "failed"
            job.message = "导出失败"
            job.error = error
            now = time.time()
            job.updated_at = now
            job.finished_at = now

    def cleanup_expired(self) -> None:
        now = time.time()
        with self._lock:
            expired = [
                job_id
                for job_id, job in self._jobs.items()
                if now - job.created_at > JOB_TTL_SECONDS
            ]
            for job_id in expired:
                del self._jobs[job_id]


batch_job_store = WorkorderBatchJobStore()


async def run_batch_export_job(job_id: str, payload: WorkOrderBatchGenerateRequest) -> None:
    """在线程池中执行批量导出，并通过回调写入真实进度。"""

    def on_progress(current: int, total: int, phase: str, message: str = "") -> None:
        batch_job_store.update_progress(
            job_id,
            current=current,
            total=total,
            phase=phase,
            message=message,
            status=JOB_STATUS_RUNNING,
        )

    batch_job_store.update_progress(
        job_id,
        current=0,
        total=max(len(payload.records) + 1, 1),
        phase="running",
        message="开始生成工作单…",
        status=JOB_STATUS_RUNNING,
    )

    try:
        artifact = await asyncio.to_thread(
            generate_workorder_batch_artifact,
            payload,
            on_progress,
        )
        batch_job_store.complete(job_id, artifact)
        logger.info("批量导出任务完成: job_id=%s filename=%s", job_id, artifact.filename)
    except Exception as exc:  # noqa: BLE001
        logger.exception("批量导出任务失败: job_id=%s", job_id)
        batch_job_store.fail(job_id, str(exc))
