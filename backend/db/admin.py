"""Admin DB helpers — compatibility facade.

Implementation is split by domain:

- ``backend.db.admin_dashboard`` — dashboard KPIs
- ``backend.db.layer_metadata`` — map layer metadata
- ``backend.db.admin_users`` — user management
- ``backend.db.operation_logs`` — site operation logs

Importing from ``backend.db.admin`` remains supported. Tests that mock
DB primitives should patch the module where they are used
(e.g. ``backend.db.layer_metadata.fetch``).
"""

from __future__ import annotations

from backend.db.admin_dashboard import get_dashboard_stats  # noqa: F401
from backend.db.admin_users import (  # noqa: F401
    UserDict,
    create_user,
    delete_user,
    get_user_by_id,
    list_users,
    reset_user_password,
    update_user,
)
from backend.db.layer_metadata import (  # noqa: F401
    ADMIN_SCHEMA,
    LAYER_METADATA_TABLE,
    LayerMetadataDict,
    batch_upsert_layer_metadata,
    ensure_layer_metadata_storage,
    get_enabled_map_view,
    get_enabled_reference_layer,
    get_layer_metadata_by_key,
    list_enabled_map_views,
    list_enabled_reference_layers,
    list_layer_metadata,
    sync_layer_metadata,
)
from backend.db.map_queries import list_map_views, list_reference_layers  # noqa: F401
from backend.db.operation_logs import (  # noqa: F401
    OPERATION_LOG_ACTION_DELETE_OTHER_PEST_SITE,
    OPERATION_LOG_ACTION_DELETE_WHITE_MOTH_SITE,
    OPERATION_LOG_TABLE,
    ensure_operation_log_storage,
    list_operation_logs,
)
from backend.db.pool import ensure_pool, fetch, fetchrow  # noqa: F401
