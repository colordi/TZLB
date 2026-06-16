from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


IMAGE_STRATEGY_UPLOADED = "uploaded_images"
IMAGE_STRATEGY_WHITE_MOTH_AUTO = "white_moth_auto_images"

SURVEY_IMPORT_SPRING_INCHWORM = "spring_inchworm"
SURVEY_IMPORT_GUO_HUAI_INCHWORM = "guo_huai_inchworm"
SURVEY_IMPORT_OTHER_PEST = "other_pest"
SURVEY_IMPORT_MEI_GUO_BAI_E = "mei_guo_bai_e"
WORKORDER_TEMPLATE_FILENAME = "林业有害生物防治工作单模板.docx"


@dataclass(frozen=True, slots=True)
class PestRegistryEntry:
    key: str
    label: str
    control_type: str
    tasks: tuple[str, ...]
    field_keys: tuple[str, ...]
    required_field_keys: tuple[str, ...]
    number_field_keys: tuple[str, ...]
    template_filename: str
    payload_field_keys: tuple[str, ...]
    default_region: str
    record_defaults: dict[str, Any] = field(default_factory=dict)
    context_defaults: dict[str, Any] = field(default_factory=dict)
    context_overrides: dict[str, Any] = field(default_factory=dict)
    image_strategy: str = IMAGE_STRATEGY_UPLOADED
    survey_import_strategy: str | None = None


COMMON_REQUIRED_FIELD_KEYS = (
    "survey_date",
    "locality",
    "location_id",
    "location_name",
    "description",
)

COMMON_PAYLOAD_FIELD_KEYS = (
    "survey_date",
    "locality",
    "location_id",
    "location_name",
    "description",
    "note",
    "images",
)

CHI_HUO_FIELD_KEYS = (
    "survey_date",
    "locality",
    "location_id",
    "location_name",
    "note",
    "description",
)

OTHER_PEST_FIELD_KEYS = (
    "survey_date",
    "locality",
    "location_id",
    "location_name",
    "plot_type",
    "pest_name",
    "host_plant",
    "note",
    "description",
)

MEI_GUO_BAI_E_FIELD_KEYS = (
    "survey_date",
    "locality",
    "location_id",
    "location_name",
    "green_space_type",
    "pest_hosts",
    "damaged_plant_count",
    "web_nest_count",
    "note",
    "description",
)

PEST_REGISTRY: tuple[PestRegistryEntry, ...] = (
    PestRegistryEntry(
        key="春尺蠖",
        label="春尺蠖",
        control_type="春尺蠖防治",
        tasks=("2026春尺蠖防治",),
        field_keys=CHI_HUO_FIELD_KEYS,
        required_field_keys=COMMON_REQUIRED_FIELD_KEYS,
        number_field_keys=(),
        template_filename=WORKORDER_TEMPLATE_FILENAME,
        payload_field_keys=COMMON_PAYLOAD_FIELD_KEYS,
        default_region="乡镇",
        record_defaults={"plot_type": "平原造林"},
        context_defaults={
            "plot_type": "平原造林",
            "damaged_plant_count": "10",
            "green_space_type": "平原造林",
            "web_nest_count": "0",
        },
        context_overrides={
            "pest_name": "",
            "host_plant": "",
            "pest_species": "春尺蠖",
            "host": "杨树",
            "tree_height": "8米上",
        },
        survey_import_strategy=SURVEY_IMPORT_SPRING_INCHWORM,
    ),
    PestRegistryEntry(
        key="国槐尺蠖",
        label="国槐尺蠖",
        control_type="国槐尺蠖防治",
        tasks=(
            "2026国槐尺蠖第一代防治",
            "2026国槐尺蠖第二代防治",
            "2026国槐尺蠖第三代防治",
        ),
        field_keys=CHI_HUO_FIELD_KEYS,
        required_field_keys=COMMON_REQUIRED_FIELD_KEYS,
        number_field_keys=(),
        template_filename=WORKORDER_TEMPLATE_FILENAME,
        payload_field_keys=COMMON_PAYLOAD_FIELD_KEYS,
        default_region="乡镇",
        record_defaults={"plot_type": "平原造林"},
        context_defaults={
            "plot_type": "平原造林",
            "damaged_plant_count": "10",
            "green_space_type": "平原造林",
            "web_nest_count": "0",
        },
        context_overrides={
            "pest_name": "",
            "host_plant": "",
            "pest_species": "国槐尺蠖",
            "host": "国槐",
            "tree_height": "8米下",
        },
        survey_import_strategy=SURVEY_IMPORT_GUO_HUAI_INCHWORM,
    ),
    PestRegistryEntry(
        key="美国白蛾",
        label="美国白蛾",
        control_type="美国白蛾防治",
        tasks=("2026美国白蛾第一代防治",),
        field_keys=MEI_GUO_BAI_E_FIELD_KEYS,
        required_field_keys=COMMON_REQUIRED_FIELD_KEYS,
        number_field_keys=("damaged_plant_count", "web_nest_count"),
        template_filename=WORKORDER_TEMPLATE_FILENAME,
        payload_field_keys=(
            *COMMON_PAYLOAD_FIELD_KEYS,
            "green_space_type",
            "pest_hosts",
            "damaged_plant_count",
            "web_nest_count",
        ),
        default_region="乡镇",
        context_defaults={"tree_height": "8米下/中/下"},
        context_overrides={"pest_species": "美国白蛾"},
        image_strategy=IMAGE_STRATEGY_WHITE_MOTH_AUTO,
        survey_import_strategy=SURVEY_IMPORT_MEI_GUO_BAI_E,
    ),
    PestRegistryEntry(
        key="其他害虫",
        label="其他害虫",
        control_type="其他害虫防治",
        tasks=("2026其他害虫防治",),
        field_keys=OTHER_PEST_FIELD_KEYS,
        required_field_keys=COMMON_REQUIRED_FIELD_KEYS,
        number_field_keys=(),
        template_filename=WORKORDER_TEMPLATE_FILENAME,
        payload_field_keys=(
            *COMMON_PAYLOAD_FIELD_KEYS,
            "plot_type",
            "pest_name",
            "host_plant",
        ),
        default_region="城区",
        context_defaults={
            "tree_height": "8米下",
            "damaged_plant_count": "10",
            "web_nest_count": "0",
        },
        survey_import_strategy=SURVEY_IMPORT_OTHER_PEST,
    ),
)

PEST_REGISTRY_BY_KEY = {entry.key: entry for entry in PEST_REGISTRY}


def normalize_pest_type(value: str) -> str:
    return str(value or "").strip()


def normalize_task_type(value: str) -> str:
    return str(value or "").strip()


def list_pest_configs() -> tuple[PestRegistryEntry, ...]:
    return PEST_REGISTRY


def get_pest_config(pest_type: str) -> PestRegistryEntry:
    normalized = normalize_pest_type(pest_type)
    if not normalized:
        raise ValueError("害虫类型不能为空")

    config = PEST_REGISTRY_BY_KEY.get(normalized)
    if config is None:
        raise ValueError(f"不支持的害虫类型：{normalized}")
    return config


def validate_pest_type(pest_type: str) -> str:
    return get_pest_config(pest_type).key


def validate_task_type(pest_type: str, task_type: str) -> str:
    config = get_pest_config(pest_type)
    normalized = normalize_task_type(task_type)
    if not normalized:
        raise ValueError("统防统治类型不能为空")
    if normalized != config.control_type:
        raise ValueError(f"{config.key} 不支持统防统治类型：{normalized}")
    return normalized
