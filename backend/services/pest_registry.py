from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.config import get_settings


IMAGE_STRATEGY_UPLOADED = "uploaded_images"
# 从点位截图目录 + images/{调查日期}/ 按编号自动装配（美国白蛾、其他害虫等）
IMAGE_STRATEGY_AUTO_DISK = "auto_disk_images"
# 历史别名，与 IMAGE_STRATEGY_AUTO_DISK 等价
IMAGE_STRATEGY_WHITE_MOTH_AUTO = IMAGE_STRATEGY_AUTO_DISK

SURVEY_IMPORT_SPRING_INCHWORM = "spring_inchworm"
SURVEY_IMPORT_GUO_HUAI_INCHWORM = "guo_huai_inchworm"
SURVEY_IMPORT_OTHER_PEST = "other_pest"
SURVEY_IMPORT_MEI_GUO_BAI_E = "mei_guo_bai_e"
WORKORDER_TEMPLATE_FILENAME = "林业有害生物防治工作单模板.docx"
DEFAULT_TASK_TEMPLATE = "{year}{pest}{generation}防治"
GENERATION_NONE: tuple[str | None, ...] = (None,)
GENERATIONS_THREE: tuple[str | None, ...] = ("第一代", "第二代", "第三代")


@dataclass(frozen=True, slots=True)
class PestRegistryEntry:
    key: str
    label: str
    control_type: str
    task_template: str
    generations: tuple[str | None, ...]
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
    screenshot_dir_attr: str | None = None


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
        task_template=DEFAULT_TASK_TEMPLATE,
        generations=GENERATION_NONE,
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
        screenshot_dir_attr="point_screenshot_dir",
    ),
    PestRegistryEntry(
        key="国槐尺蠖",
        label="国槐尺蠖",
        control_type="国槐尺蠖防治",
        task_template=DEFAULT_TASK_TEMPLATE,
        generations=GENERATIONS_THREE,
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
        screenshot_dir_attr="sophora_point_screenshot_dir",
    ),
    PestRegistryEntry(
        key="美国白蛾",
        label="美国白蛾",
        control_type="美国白蛾防治",
        task_template=DEFAULT_TASK_TEMPLATE,
        generations=GENERATIONS_THREE,
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
        screenshot_dir_attr="meiguobaie_point_screenshot_dir",
    ),
    PestRegistryEntry(
        key="其他害虫",
        label="其他害虫",
        control_type="其他害虫防治",
        task_template=DEFAULT_TASK_TEMPLATE,
        generations=GENERATION_NONE,
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
        image_strategy=IMAGE_STRATEGY_AUTO_DISK,
        survey_import_strategy=SURVEY_IMPORT_OTHER_PEST,
        screenshot_dir_attr="other_pest_point_screenshot_dir",
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


def get_screenshot_dir(pest_type: str) -> Path | None:
    """返回害虫对应的点位截图目录，未配置时返回 None。"""

    config = get_pest_config(pest_type)
    if not config.screenshot_dir_attr:
        return None
    settings = get_settings()
    return getattr(settings, config.screenshot_dir_attr)


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


def build_task(entry: PestRegistryEntry, year: int, generation: str | None) -> str:
    """根据害虫配置、年份和世代渲染统防统治任务名。"""

    return entry.task_template.format(
        year=year,
        pest=entry.key,
        generation=generation or "",
    )


def list_tasks(entry: PestRegistryEntry, year: int) -> tuple[str, ...]:
    """列出某害虫在指定年份下的所有任务名。"""

    return tuple(build_task(entry, year, gen) for gen in entry.generations)


def normalize_generation(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value or "").strip()
    return normalized or None


def validate_generation(pest_type: str, generation: str | None) -> str | None:
    """校验世代值是否在该害虫的注册范围内，返回归一化后的世代值。"""

    config = get_pest_config(pest_type)
    normalized = normalize_generation(generation)
    if normalized is None:
        if None not in config.generations:
            raise ValueError(f"{config.key} 需要指定世代")
    elif normalized not in config.generations:
        raise ValueError(f"{config.key} 不支持世代：{normalized}")
    return normalized
