from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from backend.config import get_settings
from backend.services.docgen.constants import DOC_CONVERT_FILTER
from backend.services.docgen.render import replace_suffix


def convert_docx_bytes_to_doc(filename: str, content: bytes) -> tuple[str, bytes]:
    """使用 LibreOffice 将 docx 字节流转换为 doc。"""

    settings = get_settings()
    source_filename = replace_suffix(filename, ".docx")
    target_filename = replace_suffix(filename, ".doc")

    with tempfile.TemporaryDirectory(dir=settings.temp_dir, prefix="workorder_export_") as workdir:
        workdir_path = Path(workdir)
        source_path = workdir_path / source_filename
        target_path = workdir_path / target_filename
        source_path.write_bytes(content)

        try:
            subprocess.run(
                [
                    settings.libreoffice_bin,
                    "--headless",
                    "--convert-to",
                    f"doc:{DOC_CONVERT_FILTER}",
                    "--outdir",
                    str(workdir_path),
                    str(source_path),
                ],
                check=True,
                capture_output=True,
                timeout=settings.libreoffice_timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"未找到 LibreOffice 命令行工具：{settings.libreoffice_bin}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("LibreOffice 转换超时，请稍后重试。") from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="ignore").strip() if exc.stderr else ""
            stdout = exc.stdout.decode("utf-8", errors="ignore").strip() if exc.stdout else ""
            detail = stderr or stdout or "未知错误"
            raise RuntimeError(f"LibreOffice 转换失败：{detail}") from exc

        if not target_path.exists():
            raise RuntimeError("LibreOffice 转换失败：未生成 .doc 文件。")

        return target_filename, target_path.read_bytes()
