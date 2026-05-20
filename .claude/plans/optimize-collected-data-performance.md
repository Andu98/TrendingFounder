# Plan: Optimize Collected Data Page Status Change Performance

## Context

When clicking a status button on the "Collected Data" page with "show reviewed" filter off, the page takes 4-5 seconds to refresh instead of responding instantly. This is a critical UX issue that slows down the review workflow.

The slowness is caused by:
1. **Two separate database round trips**: The `load_collected_data()` function first calls the RPC, then makes an additional query via `_enrich_domain_details()` to fetch missing fields.
2. **N+1 query pattern**: The RPC computes `comment_count` with a correlated subquery that executes once per row (e.g., 50 times for a 50-row page).
3. **Missing composite indexes**: The query would benefit from `domain_observations(observed_date, domain_id)` and `domains(review_status, id)`.

## Goal

Make status changes effectively instantaneous (< 1 second) by:
- Reducing to a single database round trip
- Optimizing the comment count aggregation
- Adding appropriate indexes

## Files to Modify

### 1. Supabase Schema: `supabase/schemas/006_optimize_domain_query.sql`

**New migration file** that:
- Adds composite indexes
- Modifies the `get_domains_for_range()` function to include all necessary fields and optimize comment count

**Indexes:**
```sql
CREATE INDEX IF NOT EXISTS idx_observations_observed_date_domain_id 
ON domain_observations (observed_date, domain_id);

CREATE INDEX IF NOT EXISTS idx_domains_review_status_id 
ON domains (review_status, id);
```

**RPC modifications:**
- Add missing fields from `domains` table: `first_seen_at`, `first_country_code`, `first_country_name`, `first_ranking_type`, `llm_target_users`, `llm_localization_angle`, `llm_risk_notes`
- Replace correlated `comment_count` subquery with a LEFT JOIN to a pre-aggregated CTE of comment counts by domain_id
- Keep all existing fields and logic intact

**Implementation detail:**
```sql
WITH params AS (...),
aggregated AS (...),
comment_counts AS (
    SELECT domain_id, COUNT(*) as comment_count
    FROM domain_comments
    GROUP BY domain_id
)
SELECT 
    counted.*,
    COALESCE(cc.comment_count, 0) as comment_count
FROM counted
LEFT JOIN comment_counts cc ON cc.domain_id = counted.id
...
```

### 2. Application: `app/data_loader.py`

**Changes:**
- Remove the `_enrich_domain_details()` function entirely (lines 175-206)
- Remove the call to `_enrich_domain_details()` in `load_collected_data()` (line 332)
- Update `_format_today_dataframe()`: simplify `First seen` column logic since `first_seen_at` will always be present from the RPC. Change:
  ```python
  df["First seen"] = _series(df, "first_seen_at").fillna(_series(df, "first_seen_date")).fillna("")
  ```
  to:
  ```python
  df["First seen"] = _series(df, "first_seen_at").fillna("")
  ```

**No other changes needed** - the RPC will now return all required fields.

### 3. Optional: `app/data_loader.py` cache TTL

The current TTL is 30 seconds. We could consider reducing it, but not necessary for this fix. The cache clearing on update already ensures fresh data.

## Implementation Order

1. Apply the database migration first (can be done independently)
2. Update application code to remove enrichment and simplify formatting
3. Test locally with Streamlit app: measure status change latency before and after
4. Verify all fields display correctly and status changes persist

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Migration breaks RPC if syntax incorrect | Test migration on local Supabase instance first (if available) or apply to staging |
| Removing `_enrich_domain_details()` breaks if other code uses it | Search codebase for direct calls - it's a private function `_enrich_domain_details()`, only called in `load_collected_data()` |
| Missing field causes UI error | Verify RPC returns all fields used in `_format_today_dataframe()` and `render_domain_table()` by listing them carefully |
| Index creation locks table or slows production | Indexes are created with `IF NOT EXISTS` and should be fast on PostgreSQL. Monitor Supabase if needed. |

## Verification

### Before Changes
1. Open browser DevTools → Network tab
2. Note time for `/rpc/get_domains_for_range` call and any subsequent `domains` query
3. Click status button, measure total time to see updated status

### After Changes
1. Should see only one RPC call (no extra `domains` query)
2. RPC should complete faster
3. Status change should reflect in < 1 second

### Functional
- All domain columns display correctly (First seen, Country, Category, etc.)
- Filters (status, category, search, date range, etc.) work
- Pagination works
- Comments still load correctly

## Rollback Plan

If issues arise:
- Revert migration (DROP INDEX IF EXISTS; RESTORE original function)
- Restore `_enrich_domain_details()` function and its call in `load_collected_data()`
- Restore the old `First seen` fallback logic

Since the changes are additive (new indexes, new fields in RPC) and removal of a helper function, rollback is straightforward.
