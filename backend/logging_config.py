"""应用结构化日志配置。

日志输出到 stderr，格式包含时间、级别、request_id、logger 名和消息，
便于容器化或服务化部署时由外部日志收集器统一处理。
"""

from __future__ import annotations

import logging
import sys
from typing import Any

REQUEST_ID_EXTRA_KEY = "request_id"


class RequestIdFormatter(logging.Formatter):
    """在日志格式中安全嵌入 request_id，缺失时显示为 -。"""

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, REQUEST_ID_EXTRA_KEY, None) or "-"
        record.request_id = request_id  # type: ignore[attr-defined]
        return super().format(record)


def configure_logging(level: str | int = logging.INFO) -> None:
    """配置应用日志：统一格式、级别和输出目标。"""

    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    formatter = RequestIdFormatter(
        fmt="%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 避免重复添加 handler（例如单元测试多次调用）
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.addHandler(handler)

    # 第三方库默认保持 WARNING，减少噪声
    for noisy_name in ("uvicorn", "uvicorn.access", "fastapi"):
        logging.getLogger(noisy_name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取带 request_id 支持的 logger。"""

    return logging.getLogger(name)


def log_with_request_id(logger: logging.Logger, level: int, message: str, request_id: str | None = None, **kwargs: Any) -> None:
    """记录一条带 request_id 的日志。"""

    extra = {REQUEST_ID_EXTRA_KEY: request_id or "-"}
    extra.update(kwargs)
    logger.log(level, message, extra=extra)
