# Survey Data Import for Work Orders

## Context

The forestry work order system currently requires fully manual data entry. However, survey data in the database (specifically `survey.chun_chi_huo_larva` joined with `sites.poplar_sites`) already contains sufficient information to pre-fill work order records for sites with pest damage. This feature automates the import of survey data into work order records, reducing manual effort from ~10 fields per record to just reviewing and tweaking auto-filled data.

Scope: Spring inchworm (春尺蠖) larva survey data only. Other pest types can be added later.

## Design

### User Flow

1. User is on the Work Order page with pest type set to "春尺蠖"
2. User clicks "Import from Survey Data" button (visible only for 春尺蠖 pest type)
3. A dialog opens with a date picker (defaults to today)
4. Backend queries survey records where damage level is not blank/white for the selected date
5. Dialog displays a table of matching records with checkboxes (select all by default)
6. User confirms, selected records are appended to the work order table with all fields auto-filled
7. User can edit any field before generating the work order document

### Backend API

**Endpoint:** `GET /api/survey/candidates`

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date` | `string` (YYYY-MM-DD) | today | Survey date to query |

**Query:**
```sql
SELECT
    l."编号" AS location_id,
    l."调查日期" AS survey_date,
    l."总虫口数" AS total_insect_count,
    l."危害程度" AS damage_level,
    l."备注" AS note,
    s."乡镇" AS town_or_street,
    s."村" AS location_name
FROM survey.chun_chi_huo_larva l
JOIN sites.poplar_sites s ON l."编号" = s."编号"
WHERE l."调查日期" = $1
  AND l."危害程度" IS NOT NULL
  AND l."危害程度" NOT IN ('', '白')
ORDER BY s."乡镇", l."编号"
```

**Response:** Array of work-order-compatible records:
```json
[
  {
    "survey_date": "2026-04-01",
    "town_or_street": "于家务乡",
    "location_id": "YF0069",
    "location_name": "神仙村",
    "total_insect_count": 50,
    "damage_level": "重",
    "note": "",
    "description": "于家务乡神仙村YF0069点位，调查发现春尺蠖幼虫危害程度为重，平均每标准枝10头。建议立即组织防治作业，并优先复核周边相邻点位。"
  }
]
```

Field values are returned in the format expected by the existing `WorkOrderRecord` schema, so the frontend can directly append them to the records array.

### Description Template Generation

The backend generates a stable two-sentence description based on location, damage level, and the derived average insect count per standard branch:

**Base template:**
```text
{点位信息}，调查发现春尺蠖幼虫危害程度为{危害程度表达}，平均每标准枝{均虫口表达}。{处置建议}
```

**Location prefix:**
- Concatenate `town_or_street + location_name + location_id` after trimming
- If any of them is non-empty, render as `{点位前缀}点位`

**Damage level expression:**
| Damage Level | Rendered text | Advice |
|-------------|---------------|--------|
| 重 | `重` | `建议立即组织防治作业，并优先复核周边相邻点位。` |
| 中 | `中` | `建议尽快安排防治，并持续跟踪虫情变化。` |
| 轻 | `轻` | `建议加强巡查，视虫情发展适时处置。` |
| other non-empty value | original value | `建议结合现场情况制定防治措施并复核虫情。` |
| empty / NULL | `待判定` | `建议复核现场危害情况并及时补录调查结果。` |

**Average insect count expression:**
- If `total_insect_count` has a value, compute `total_insect_count / 5` and render the result
- Always round the result up to the next integer and render it without any decimal part
- Examples: `50 -> 10头`, `28 -> 6头`, `6 -> 2头`
- If `total_insect_count` is NULL, render `未记录`

**Note handling:**
- `note` remains a separate field in the response
- `note` is not merged into `description`

### Frontend Components

**New file: `SurveyImportDialog.vue`**

A modal dialog containing:
- Date picker input (bound to query parameter)
- "Query" button to fetch candidates from backend
- Results table with columns: checkbox, location_id, town_or_street, location_name, total_insect_count, damage_level
- Select all / deselect all toggle
- Record count display ("N records found, M selected")
- "Import" button (disabled when nothing selected)
- Loading and empty states

**Modified: `WorkOrderView.vue`**

- Add "Import from Survey Data" button next to "Add Record" button
- Button only visible when `pestType === '春尺蠖'`
- On import confirmation, append selected records to the `records` array using `normalizeRecordForPest()`

**New file: `frontend/src/api/survey.js`**

Single function: `fetchSurveyCandidates(date)` -> `GET /api/survey/candidates?date={date}`

### Backend Files

**New file: `backend/routers/survey.py`**
- Single route `GET /candidates` returning candidate records

**Modified: `backend/db/postgres.py`**
- New function `fetch_survey_candidates(date)` executing the query above

**Modified: `backend/main.py`**
- Register survey router at `/api/survey`

## Data Flow

```
User clicks "Import" button
  -> SurveyImportDialog opens (default date = today)
  -> User clicks "Query"
  -> GET /api/survey/candidates?date=2026-04-01
  -> Backend: JOIN survey + sites, filter damage, generate descriptions
  -> Response: array of pre-filled records
  -> Dialog shows table with checkboxes
  -> User selects records, clicks "Import"
  -> Records appended to WorkOrderView.records[]
  -> User reviews/edits in existing table
  -> User clicks "Generate" (existing flow)
```

## Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/routers/survey.py` | Create | New API router for survey candidates |
| `backend/db/postgres.py` | Edit | Add `fetch_survey_candidates()` function |
| `backend/main.py` | Edit | Register survey router |
| `frontend/src/api/survey.js` | Create | API client function |
| `frontend/src/components/workorder/SurveyImportDialog.vue` | Create | Import dialog component |
| `frontend/src/views/WorkOrderView.vue` | Edit | Add import button and dialog integration |

## Verification

1. Start backend: `cd backend && uvicorn backend.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to Work Order page, select 春尺蠖 pest type
4. Verify "Import from Survey Data" button appears
5. Click the button, verify dialog opens with today's date
6. Click "Query", verify records appear (should show records with damage != blank/white)
7. Select some records, click "Import"
8. Verify records appear in the work order table with all fields filled
9. Verify description field contains the auto-generated template text
10. Verify the "Generate" button works normally with imported records
11. Test with a date that has no survey data - verify empty state message
12. Test edge case: importing when table already has records (should append, not replace)
