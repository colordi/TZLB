from __future__ import annotations

from dataclasses import dataclass

MAX_IMAGES = 4
IMAGE_WIDTH_MM = 70
DOC_MEDIA_TYPE = "application/msword"
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ZIP_MEDIA_TYPE = "application/zip"
DOC_CONVERT_FILTER = "MS Word 97"
SUPPORTED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
SUPPORTED_IMAGE_FORMAT_LABEL = "JPEG、PNG、WebP"
DOC_FIELD_MAPPING = {
    "description": "detailed_description",
    "host_plant": "host",
    "pest_name": "pest_species",
}


@dataclass(slots=True)
class GeneratedArtifact:
    filename: str
    media_type: str
    content: bytes
