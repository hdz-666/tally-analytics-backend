-- ─────────────────────────────────────────────────────────────────────────────
-- Phase 1 — Company A only
-- All Tally tables live in the tallydb schema.
-- Materialized views and stock_forecast table are created in public schema.
-- ─────────────────────────────────────────────────────────────────────────────

-- ─────────────────────────────────────────────
-- 0. stock_forecast — written by Python service
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.stock_forecast (
    item            varchar(1024)   NOT NULL,
    stock_group     varchar(1024),
    forecast_month  date            NOT NULL,
    forecast_qty    numeric(15,4)   NOT NULL,
    lower_bound     numeric(15,4),
    upper_bound     numeric(15,4),
    current_stock   numeric(15,4),
    reorder_point   numeric(15,4),
    reorder_qty     numeric(15,4),
    needs_reorder   boolean,
    model_used      varchar(64),
    created_at      timestamptz DEFAULT now(),
    PRIMARY KEY (item, forecast_month)
);

CREATE INDEX IF NOT EXISTS idx_stock_forecast_item
    ON public.stock_forecast (item);


-- ─────────────────────────────────────────────
-- 1. Current stock — Company A (Phase 1 fallback)
-- ─────────────────────────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS public.v_current_stock AS
SELECT
    si.name                         AS name,
    si.parent                       AS stock_group,
    COALESCE(si.closing_balance, 0) AS closing_balance,
    COALESCE(si.closing_value,   0) AS closing_value,
    COALESCE(si.closing_rate,    0) AS closing_rate
FROM tallydb.mst_stock_item si
WHERE si.closing_balance IS NOT NULL
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_current_stock_name
    ON public.v_current_stock (name);


-- ─────────────────────────────────────────────
-- 2. Monthly sales per item — Company A
-- mst_vouchertype parent lookup covers all Sales sub-types automatically
-- (Tax Invoice, Retail Invoice, Export Invoice, etc.)
-- quantity < 0 = stock going out (sales); credit notes excluded automatically.
-- ─────────────────────────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS public.v_sales_monthly AS
SELECT
    DATE_TRUNC('month', v.date)::date   AS month,
    i.item,
    si.parent                           AS stock_group,
    SUM(ABS(i.quantity))                AS sold_qty,
    SUM(ABS(i.amount))                  AS sold_amount
FROM tallydb.trn_voucher v
JOIN tallydb.trn_inventory i     ON i.guid = v.guid
LEFT JOIN tallydb.mst_stock_item si ON si.name = i.item
WHERE v.voucher_type IN (
        SELECT name FROM tallydb.mst_vouchertype WHERE parent = 'Sales'
    )
  AND i.quantity < 0
GROUP BY 1, 2, 3
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_sales_monthly_uk
    ON public.v_sales_monthly (month, item);
CREATE INDEX IF NOT EXISTS idx_v_sales_monthly_item
    ON public.v_sales_monthly (item);
CREATE INDEX IF NOT EXISTS idx_v_sales_monthly_month
    ON public.v_sales_monthly (month);


-- ─────────────────────────────────────────────
-- 3. Monthly sales by stock group
-- ─────────────────────────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS public.v_sales_by_group AS
SELECT
    month,
    COALESCE(stock_group, 'Uncategorised') AS stock_group,
    SUM(sold_qty)                           AS sold_qty,
    SUM(sold_amount)                        AS sold_amount
FROM public.v_sales_monthly
GROUP BY 1, 2
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_sales_by_group_uk
    ON public.v_sales_by_group (month, stock_group);
CREATE INDEX IF NOT EXISTS idx_v_sales_by_group
    ON public.v_sales_by_group (stock_group, month);


-- ─────────────────────────────────────────────
-- 4. Monthly purchases by stock group — Company A
-- quantity > 0 = stock coming in; purchase returns excluded automatically.
-- ─────────────────────────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS public.v_purchase_by_group AS
SELECT
    DATE_TRUNC('month', v.date)::date       AS month,
    COALESCE(si.parent, 'Uncategorised')    AS stock_group,
    SUM(ABS(i.quantity))                    AS purchased_qty,
    SUM(ABS(i.amount))                      AS purchased_amount
FROM tallydb.trn_voucher v
JOIN tallydb.trn_inventory i     ON i.guid = v.guid
LEFT JOIN tallydb.mst_stock_item si ON si.name = i.item
WHERE v.voucher_type IN (
        SELECT name FROM tallydb.mst_vouchertype WHERE parent = 'Purchase'
    )
  AND i.quantity > 0
GROUP BY 1, 2
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_purchase_by_group_uk
    ON public.v_purchase_by_group (month, stock_group);
CREATE INDEX IF NOT EXISTS idx_v_purchase_by_group
    ON public.v_purchase_by_group (stock_group, month);


-- ─────────────────────────────────────────────
-- 5. Top moving items by total sales value
-- ─────────────────────────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS public.v_top_moving_items AS
SELECT
    item,
    COALESCE(stock_group, 'Uncategorised') AS stock_group,
    SUM(sold_qty)                           AS total_qty,
    SUM(sold_amount)                        AS total_amount,
    COUNT(DISTINCT month)                   AS months_active
FROM public.v_sales_monthly
GROUP BY 1, 2
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_top_moving_uk
    ON public.v_top_moving_items (item);
CREATE INDEX IF NOT EXISTS idx_v_top_moving
    ON public.v_top_moving_items (total_amount DESC);


-- ─────────────────────────────────────────────
-- 6. Reorder alerts — regular view, always current
--    No refresh needed — joins two fast sources:
--    v_current_stock (materialized) + stock_forecast (table)
-- ─────────────────────────────────────────────
CREATE OR REPLACE VIEW public.v_reorder_alerts AS
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
) sf ON sf.item = cs.name;


-- ─────────────────────────────────────────────
-- Refresh after each monthly sync (run in order)
-- ─────────────────────────────────────────────
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_current_stock;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_sales_monthly;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_sales_by_group;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_purchase_by_group;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_top_moving_items;
-- v_reorder_alerts is a regular view — no refresh needed
