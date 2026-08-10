"""Pydantic request/response schemas (split by domain)."""

from __future__ import annotations

from backend.schemas.admin import (  # noqa: F401
    AdminUserResponse,
    BatchUpdateLayersRequest,
    CreateUserRequest,
    DashboardStatsResponse,
    LayerMetadataItem,
    LayerMetadataResponse,
    ResetPasswordRequest,
    TaskViewBaseSource,
    TaskViewDefinitionRequest,
    TaskViewFilters,
    TaskViewMutationResponse,
    TaskViewPreviewResponse,
    TaskViewRelatedSource,
    TaskViewSourcesResponse,
    UpdateUserRequest,
)
from backend.schemas.auth import (  # noqa: F401
    AuthenticatedUser,
    AuthSessionResponse,
    LoginRequest,
)
from backend.schemas.data_manager import (  # noqa: F401
    DataManagerChangeLogItem,
    DataManagerChangeLogListResponse,
    DataManagerColumnInfo,
    DataManagerRowCreateRequest,
    DataManagerRowDeleteRequest,
    DataManagerRowsResponse,
    DataManagerRowUpdateRequest,
    DataManagerTableInfo,
)
from backend.schemas.map import (  # noqa: F401
    GenericSiteCodeHintResponse,
    GenericSiteCreateRequest,
    GenericSiteResponse,
    MapViewSummary,
    OperationLogItem,
    OperationLogListResponse,
    OtherPestSiteCodeHintResponse,
    OtherPestSiteCreateRequest,
    OtherPestSiteDeleteCheckResponse,
    OtherPestSiteDeleteResponse,
    OtherPestSiteResponse,
    WhiteMothSiteCodeHintResponse,
    WhiteMothSiteCreateRequest,
    WhiteMothSiteDeleteCheckResponse,
    WhiteMothSiteDeleteResponse,
    WhiteMothSiteResponse,
)
from backend.schemas.workorder import (  # noqa: F401
    PestType,
    TaskType,
    WorkOrderBatchGenerateRequest,
    WorkOrderBatchJobCreateResponse,
    WorkOrderBatchJobStatusResponse,
    WorkOrderGenerateRequest,
    WorkOrderRecord,
)
