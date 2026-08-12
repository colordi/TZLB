"""Workorder document generation package."""

from __future__ import annotations

import subprocess
import tempfile

from backend.config import get_settings  # noqa: F401  # patch target for tests
from backend.services.docgen.constants import (  # noqa: F401
    DOC_CONVERT_FILTER,
    DOC_FIELD_MAPPING,
    DOC_MEDIA_TYPE,
    DOCX_MEDIA_TYPE,
    IMAGE_WIDTH_MM,
    MAX_IMAGES,
    SUPPORTED_IMAGE_FORMATS,
    SUPPORTED_IMAGE_FORMAT_LABEL,
    ZIP_MEDIA_TYPE,
    GeneratedArtifact,
)
from backend.services.docgen.convert import convert_docx_bytes_to_doc  # noqa: F401
from backend.services.docgen.images import (  # noqa: F401
    build_temp_image_path,
    cleanup_temp_images,
    decode_base64_image,
    ensure_image_size_limits,
    find_dated_location_image_names,
    find_point_screenshot_name,
    format_size_limit,
    image_to_rgb,
    is_image_file,
    natural_path_sort_key,
    resize_image_if_needed,
    resolve_auto_disk_images,
    resolve_meiguobaie_images,
    resolve_record_image_paths,
    sanitize_images_to_temp,
    save_base64_images,
    write_sanitized_image,
)
from backend.services.docgen.render import (  # noqa: F401
    build_context,
    build_output_filename,
    ensure_template_context_complete,
    ensure_template_markers_resolved,
    get_template_path,
    render_single_document,
    replace_suffix,
)
from backend.services.docgen.service import (  # noqa: F401
    BatchFailure,
    BatchResult,
    build_batch_zip_filename,
    build_download_artifact,
    generate_workorder_artifact,
    generate_workorder_batch_artifact,
    resolve_output_format,
)

# Re-export stdlib modules used by convert so legacy patches still resolve
# when tests patch backend.services.docgen.tempfile / subprocess.
__all__ = [
    "BatchFailure",
    "BatchResult",
    "DOC_CONVERT_FILTER",
    "DOC_FIELD_MAPPING",
    "DOC_MEDIA_TYPE",
    "DOCX_MEDIA_TYPE",
    "GeneratedArtifact",
    "IMAGE_WIDTH_MM",
    "MAX_IMAGES",
    "SUPPORTED_IMAGE_FORMATS",
    "SUPPORTED_IMAGE_FORMAT_LABEL",
    "ZIP_MEDIA_TYPE",
    "build_batch_zip_filename",
    "build_context",
    "build_download_artifact",
    "build_output_filename",
    "build_temp_image_path",
    "cleanup_temp_images",
    "convert_docx_bytes_to_doc",
    "decode_base64_image",
    "ensure_image_size_limits",
    "ensure_template_context_complete",
    "ensure_template_markers_resolved",
    "find_dated_location_image_names",
    "find_point_screenshot_name",
    "format_size_limit",
    "generate_workorder_artifact",
    "generate_workorder_batch_artifact",
    "get_settings",
    "get_template_path",
    "image_to_rgb",
    "is_image_file",
    "natural_path_sort_key",
    "render_single_document",
    "replace_suffix",
    "resize_image_if_needed",
    "resolve_auto_disk_images",
    "resolve_meiguobaie_images",
    "resolve_output_format",
    "resolve_record_image_paths",
    "sanitize_images_to_temp",
    "save_base64_images",
    "subprocess",
    "tempfile",
    "write_sanitized_image",
]
