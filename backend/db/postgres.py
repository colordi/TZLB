"""Database helpers — compatibility facade.

Implementation is split by domain:

- ``backend.db.pool`` — connection pool and query primitives
- ``backend.db.map_queries`` — map views, filters, GeoJSON
- ``backend.db.white_moth_sites`` — white moth site rules and CRUD
- ``backend.db.other_pest_sites`` — other-pest site rules and CRUD
- ``backend.db.survey_candidates`` — workorder dispatch-event import candidates

Importing from ``backend.db.postgres`` remains supported so existing
routers keep working. Unit tests that mock DB primitives should patch the
module where they are used (e.g. ``backend.db.map_queries.fetch``,
``backend.db.white_moth_sites.fetchrow``), not this facade.
"""

from __future__ import annotations

from backend.db.map_queries import (  # noqa: F401
    ADMIN_BOUNDARY_TABLE,
    BBox,
    LOCALITY_COLUMN,
    MAP_DYNAMIC_FILTER_COLUMNS,
    MAP_FILTER_VALUE_ORDER,
    MAP_MAX_LIMIT,
    MAP_POINT_DEDUPE_KEYS,
    MAP_SURVEY_DATE_KEYS,
    REFERENCE_SCHEMA,
    SURVEY_STATUS_FILTER_KEY,
    SURVEY_STATUS_FILTER_OPTIONS,
    SURVEY_STATUS_FILTER_VALUES,
    VIEW_SCHEMA,
    add_feature_collection_metadata,
    build_bbox_clause,
    build_map_view_filter_clauses,
    build_select_filter_field,
    count_non_empty_map_properties,
    dedupe_map_features,
    fetch_admin_boundary_feature_collection,
    fetch_distinct_filter_values,
    fetch_map_filter_options,
    fetch_reference_layer_feature_collection,
    fetch_survey_status_counts,
    fetch_view_feature_collection,
    get_map_view,
    get_reference_layer,
    list_map_views,
    list_reference_layers,
    map_feature_rank,
    normalize_filter_values,
    normalize_map_dedupe_value,
    normalized_geom_expression,
    records_to_feature_collection,
    resolve_filter_default_value,
    resolve_map_feature_dedupe_key,
    resolve_map_feature_survey_date,
    sort_filter_values,
)
from backend.db.other_pest_sites import (  # noqa: F401
    OTHER_PEST_SITE_CODE_EXAMPLE,
    OTHER_PEST_SITE_CODE_PATTERN,
    OTHER_PEST_SITE_CODE_PREFIX,
    OTHER_PEST_SITE_CODE_SERIAL_WIDTH,
    OTHER_PEST_SITE_LOCALITIES,
    OTHER_PEST_SITE_TABLE,
    OTHER_PEST_SURVEY_TABLE,
    OtherPestSiteCodeError,
    OtherPestSiteDuplicateError,
    check_other_pest_site_deletion,
    create_other_pest_site,
    delete_other_pest_site,
    get_other_pest_site_code_hint,
    get_other_pest_site_code_rules,
    normalize_other_pest_site_code,
    validate_other_pest_site,
)
from backend.db.pool import (  # noqa: F401
    close_pool,
    ensure_pool,
    fetch,
    fetchrow,
    quote_identifier,
)
from backend.db.survey_candidates import (  # noqa: F401
    GUO_HUAI_LARVA_TABLE,
    MEI_GUO_BAI_E_SURVEY_TABLE,
    SITE_SCHEMA,
    SITE_TABLE,
    SOPHORA_SITE_TABLE,
    SURVEY_LARVA_TABLE,
    SURVEY_SCHEMA,
    WHITE_MOTH_SITE_TABLE,
    build_chi_huo_larva_description,
    build_guo_huai_inchworm_description,
    build_point_screenshot_index,
    build_spring_inchworm_description,
    encode_image_as_data_url,
    fetch_guo_huai_inchworm_survey_candidates,
    fetch_meiguobaie_survey_candidates,
    fetch_other_pest_survey_candidates,
    fetch_site_points,
    fetch_spring_inchworm_survey_candidates,
    fetch_survey_candidates,
    fetch_survey_candidates_by_type,
    fetch_yangshu_shiye_survey_candidates,
    load_point_screenshot_images,
    serialize_date_value,
)
from backend.db.white_moth_sites import (  # noqa: F401
    WHITE_MOTH_SITE_CODE_EXAMPLE,
    WHITE_MOTH_SITE_CODE_PATTERN,
    WHITE_MOTH_SITE_PREFIX_LOCALITIES,
    WhiteMothSiteCodeError,
    WhiteMothSiteDuplicateError,
    check_white_moth_site_deletion,
    create_white_moth_site,
    delete_white_moth_site,
    get_white_moth_site_code_hint,
    get_white_moth_site_code_rules,
    normalize_white_moth_site_code,
    resolve_white_moth_site_locality,
    resolve_white_moth_site_prefix,
)
