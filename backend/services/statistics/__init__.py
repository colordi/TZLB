"""White-moth statistics service package."""

from __future__ import annotations

from backend.db.postgres import ensure_pool  # noqa: F401  # patch target for tests
from backend.services.statistics.serializers import (  # noqa: F401
    merge_locality_summary_rows,
    serialize_white_moth_daily_row,
)
from backend.services.statistics.service import (  # noqa: F401
    get_white_moth_daily_statistics,
    get_white_moth_generation_summary,
    get_white_moth_locality_summary,
)
from backend.services.statistics.sql_daily import (  # noqa: F401
    WHITE_MOTH_DAILY_COLUMNS,
    WHITE_MOTH_DAILY_SQL,
    WHITE_MOTH_ROW_FIELD_MAP,
)
from backend.services.statistics.sql_generation import (  # noqa: F401
    WHITE_MOTH_DISPATCH_FREQUENCY_SQL,
    WHITE_MOTH_GENERATION_SUMMARY_SQL,
)
from backend.services.statistics.sql_locality import (  # noqa: F401
    WHITE_MOTH_CANONICAL_LOCALITIES,
    WHITE_MOTH_LOCALITY_ORDER,
    WHITE_MOTH_LOCALITY_SEVERE_SITES_SQL,
    WHITE_MOTH_LOCALITY_SUMMARY_SQL,
    WHITE_MOTH_SEVERE_PLANT_THRESHOLD,
)
