"""应用统一异常类型与错误响应构造。

全局异常处理器使用这里的类型，把内部异常转换为对外友好的中文提示，
同时通过 request_id 让运维能在日志中追踪原始堆栈。
"""

from __future__ import annotations

from typing import Any


class BusinessError(ValueError):
    """业务规则校验失败，映射为 HTTP 400。"""


class ConfigurationError(RuntimeError):
    """配置或服务资源缺失，映射为 HTTP 500。"""


def build_error_response(detail: str, request_id: str | None = None) -> dict[str, Any]:
    """构造统一的错误响应体。"""

    body: dict[str, Any] = {"detail": detail}
    if request_id:
        body["request_id"] = request_id
    return body
