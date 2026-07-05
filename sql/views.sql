-- ─────────────────────────────────────────────────────────────────────────────
-- Phase 2 — Company A (tallydb schema) + Company B ("company_b" schema)
-- Run this AFTER company_b_schema.sql and after Company B data is loaded.
-- Drops and recreates v_current_stock to point at Company B.
-- ─────────────────────────────────────────────────────────────────────────────

-- Switch current stock source to Company B (live billing, split items)
DROP MATERIALIZED VIEW IF EXISTS public.v_reorder_alerts;
DROP MATERIALIZED VIEW IF EXISTS public.v_current_stock;

CREATE MATERIALIZED VIEW public.v_current_stock AS
SELECT
    si.name                         AS name,
    si.parent                       AS stock_group,
    COALESCE(si.closing_balance, 0) AS closing_balance,
    COALESCE(si.closing_value,   0) AS closing_value,
    COALESCE(si.closing_rate,    0) AS closing_rate
FROM company_b.mst_stock_item si
WHERE si.closing_balance IS NOT NULL
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_current_stock_name
    ON public.v_current_stock (name);

-- Recreate reorder alerts (depends on v_current_stock)
CREATE MATERIALIZED VIEW public.v_reorder_alerts AS
SELECT
    cs.name                                 AS item,
    cs.stock_group,
    cs.closing_balance                      AS current_stock,
    sf.reorder_point,
    sf.reorder_qty,
    cs.closing_balance < sf.reorder_point   AS needs_reorder
FROM public.v_current_stock cs
JOIN (
    SELECT DISTINCT ON (item)
        item, reorder_point, reorder_qty
    FROM public.stock_forecast
    ORDER BY item, created_at DESC
) sf ON sf.item = cs.name
WITH DATA;

CREATE INDEX IF NOT EXISTS idx_v_reorder_alerts
    ON public.v_reorder_alerts (needs_reorder DESC);

-- All other views (v_sales_monthly, v_sales_by_group, v_purchase_by_group,
-- v_top_moving_items) stay unchanged — they always read from tallydb (Company A).

-- ─────────────────────────────────────────────────────────────────────────────
-- Refresh after each monthly sync (run in order)
-- ─────────────────────────────────────────────────────────────────────────────
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_current_stock;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_sales_monthly;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_sales_by_group;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_purchase_by_group;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_top_moving_items;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_reorder_alerts;
