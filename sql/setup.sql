-- =============================================================================
-- Tally Analytics — complete database setup
-- Run this whole file in the Supabase SQL editor. It is safe to re-run.
--
-- Schemas
--   tallydb   Company A — complete sales, purchases and inventory.
--             Raw tables are created and filled by tally-database-loader.
--             Source for every stock, sales, forecast and area-sales view.
--   tallypnl  Company B — accounting only (no inventory items).
--             Source for the ledger and P&L views.
--   public    Analytics built on tallydb, plus tables the app writes to
--             (stock_forecast, geo_cache, party_area).
--
-- Parts (in dependency order)
--   1. tallypnl raw tables            (then sync Company B with tally-database-loader)
--   2. public stock / sales views     (tallydb)
--   3. public area-wise sales         (tallydb + party_area)
--   4. tallypnl ledger & P&L          (tallypnl; COGS from tallydb)
--   5. Refresh — run after every data sync
--
-- Re-run behaviour
--   Parts 1–2 use IF NOT EXISTS: re-running never drops data, but it also won't
--   change an existing view — DROP it first if its definition changes.
--   Part 3 recreates v_sales_by_area. Part 4 recreates its views WITH NO DATA,
--   so run Part 5 afterwards.
-- =============================================================================


-- ###############################################################################
-- PART 1 — Company B raw tables (tallypnl)
-- ###############################################################################

-- ─────────────────────────────────────────────────────────────────────────────
-- Company B raw tables (schema: tallypnl) — same structure as tallydb (Company A)
-- Run this once in Supabase SQL editor.
-- Then point tally-database-loader at schema "tallypnl" when syncing Company B.
-- Company B is accounting-only: its trn_inventory stays empty, so all
-- inventory/sales views read tallydb. ledger_pnl.sql builds on these tables.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS tallypnl;

CREATE TABLE IF NOT EXISTS tallypnl.config (
    name varchar(64) PRIMARY KEY,
    value varchar(1024)
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_group (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    primary_group varchar(1024),
    is_revenue boolean,
    is_deemedpositive boolean,
    is_reserved boolean,
    affects_gross_profit boolean,
    sort_position integer
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_ledger (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    alias varchar(256),
    description varchar(64),
    notes varchar(64),
    is_revenue boolean,
    is_deemedpositive boolean,
    opening_balance numeric(17,2),
    closing_balance numeric(17,2),
    mailing_name varchar(256),
    mailing_address varchar(1024),
    mailing_state varchar(256),
    mailing_country varchar(256),
    mailing_pincode varchar(64),
    email varchar(256),
    mobile varchar(32),
    it_pan varchar(64),
    gstn varchar(64),
    gst_registration_type varchar(64),
    gst_supply_type varchar(64),
    gst_duty_head varchar(16),
    bank_account_holder varchar(256),
    bank_account_number varchar(64),
    bank_ifsc varchar(64),
    bank_swift varchar(64),
    bank_name varchar(64),
    bank_branch varchar(64),
    bill_credit_period integer
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_vouchertype (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    numbering_method varchar(64),
    is_deemedpositive boolean,
    affects_stock boolean
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_uom (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    formalname varchar(256),
    is_simple_unit boolean,
    base_units varchar(1024),
    additional_units varchar(1024),
    conversion numeric(15,4)
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_godown (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    address varchar(1024)
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_stock_category (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024)
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_stock_group (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024)
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_stock_item (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    category varchar(1024),
    alias varchar(256),
    description varchar(64),
    notes varchar(64),
    part_number varchar(256),
    uom varchar(32),
    alternate_uom varchar(32),
    conversion numeric(15,4),
    opening_balance numeric(15,4),
    opening_rate numeric(15,4),
    opening_value numeric(17,2),
    closing_balance numeric(15,4),
    closing_rate numeric(15,4),
    closing_value numeric(17,2),
    costing_method varchar(32),
    gst_type_of_supply varchar(32),
    gst_hsn_code varchar(64),
    gst_hsn_description varchar(256),
    gst_rate numeric(9,4),
    gst_taxability varchar(32)
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_cost_category (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    allocate_revenue boolean,
    allocate_non_revenue boolean
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_cost_centre (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    category varchar(1024)
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_attendance_type (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    uom varchar(32),
    attendance_type varchar(64),
    attendance_period varchar(64)
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_employee (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    id_number varchar(256),
    date_of_joining date,
    date_of_release date,
    designation varchar(64),
    function_role varchar(64),
    location varchar(256),
    gender varchar(32),
    date_of_birth date,
    blood_group varchar(32),
    father_mother_name varchar(256),
    spouse_name varchar(256),
    address varchar(256),
    mobile varchar(32),
    email varchar(64),
    pan varchar(32),
    aadhar varchar(32),
    uan varchar(32),
    pf_number varchar(32),
    pf_joining_date date,
    pf_relieving_date date,
    pr_account_number varchar(32)
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_payhead (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    payslip_name varchar(1024),
    pay_type varchar(64),
    income_type varchar(64),
    calculation_type varchar(32),
    leave_type varchar(64),
    calculation_period varchar(32)
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_gst_effective_rate (
    item varchar(1024),
    applicable_from date,
    hsn_description varchar(256),
    hsn_code varchar(64),
    duty_head varchar(64),
    rate numeric(9,4),
    rate_per_unit numeric(9,4),
    valuation_type varchar(64),
    is_rcm_applicable boolean,
    nature_of_transaction varchar(64),
    nature_of_goods varchar(64),
    supply_type varchar(64),
    taxability varchar(64)
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_opening_batch_allocation (
    name varchar(1024),
    item varchar(1024),
    opening_balance numeric(15,4),
    opening_rate numeric(15,4),
    opening_value numeric(17,2),
    godown varchar(1024),
    manufactured_on date
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_opening_bill_allocation (
    ledger varchar(1024),
    opening_balance numeric(17,4),
    bill_date date,
    name varchar(1024),
    bill_credit_period integer,
    is_advance boolean
);

CREATE TABLE IF NOT EXISTS tallypnl.trn_closingstock_ledger (
    ledger varchar(1024),
    stock_date date,
    stock_value numeric(17,2)
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_stockitem_standard_cost (
    item varchar(1024),
    date date,
    rate numeric(15,4)
);

CREATE TABLE IF NOT EXISTS tallypnl.mst_stockitem_standard_price (
    item varchar(1024),
    date date,
    rate numeric(15,4)
);

CREATE TABLE IF NOT EXISTS tallypnl.trn_voucher (
    guid varchar(64) PRIMARY KEY,
    date date,
    voucher_type varchar(1024),
    voucher_number varchar(64),
    reference_number varchar(64),
    reference_date date,
    narration varchar(4000),
    party_name varchar(256),
    place_of_supply varchar(256),
    is_invoice boolean,
    is_accounting_voucher boolean,
    is_inventory_voucher boolean,
    is_order_voucher boolean
);

CREATE TABLE IF NOT EXISTS tallypnl.trn_accounting (
    guid varchar(64),
    ledger varchar(1024),
    amount numeric(17,2),
    amount_forex numeric(17,2),
    currency varchar(16)
);

CREATE TABLE IF NOT EXISTS tallypnl.trn_inventory (
    guid varchar(64),
    item varchar(1024),
    quantity numeric(15,4),
    rate numeric(15,4),
    amount numeric(17,2),
    additional_amount numeric(17,2),
    discount_amount numeric(17,2),
    godown varchar(1024),
    tracking_number varchar(256),
    order_number varchar(256),
    order_duedate date
);

CREATE TABLE IF NOT EXISTS tallypnl.trn_cost_centre (
    guid varchar(64),
    ledger varchar(1024),
    costcentre varchar(1024),
    amount numeric(17,2)
);

CREATE TABLE IF NOT EXISTS tallypnl.trn_cost_category_centre (
    guid varchar(64),
    ledger varchar(1024),
    costcategory varchar(1024),
    costcentre varchar(1024),
    amount numeric(17,2)
);

CREATE TABLE IF NOT EXISTS tallypnl.trn_cost_inventory_category_centre (
    guid varchar(64),
    ledger varchar(1024),
    item varchar(1024),
    costcategory varchar(1024),
    costcentre varchar(1024),
    amount numeric(17,2)
);

CREATE TABLE IF NOT EXISTS tallypnl.trn_bill (
    guid varchar(64),
    ledger varchar(1024),
    name varchar(1024),
    amount numeric(17,2),
    billtype varchar(256),
    bill_credit_period integer
);

CREATE TABLE IF NOT EXISTS tallypnl.trn_bank (
    guid varchar(64),
    ledger varchar(1024),
    transaction_type varchar(32),
    instrument_date date,
    instrument_number varchar(1024),
    bank_name varchar(64),
    amount numeric(17,2),
    bankers_date date
);

CREATE TABLE IF NOT EXISTS tallypnl.trn_batch (
    guid varchar(64),
    item varchar(1024),
    name varchar(1024),
    quantity numeric(15,4),
    amount numeric(17,2),
    godown varchar(1024),
    destination_godown varchar(1024),
    tracking_number varchar(1024)
);

CREATE TABLE IF NOT EXISTS tallypnl.trn_inventory_additional_cost (
    guid varchar(64),
    ledger varchar(1024),
    amount numeric(17,2),
    additional_allocation_type varchar(32),
    rate_of_invoice_tax numeric(9,4)
);

CREATE TABLE IF NOT EXISTS tallypnl.trn_employee (
    guid varchar(64),
    category varchar(1024),
    employee_name varchar(1024),
    amount numeric(17,2),
    employee_sort_order integer
);

CREATE TABLE IF NOT EXISTS tallypnl.trn_payhead (
    guid varchar(64),
    category varchar(1024),
    employee_name varchar(1024),
    employee_sort_order integer,
    payhead_name varchar(1024),
    payhead_sort_order integer,
    amount numeric(17,2)
);

CREATE TABLE IF NOT EXISTS tallypnl.trn_attendance (
    guid varchar(64),
    employee_name varchar(1024),
    attendancetype_name varchar(1024),
    time_value numeric(17,2),
    type_value numeric(17,2)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_trn_voucher_date
    ON tallypnl.trn_voucher(date);
CREATE INDEX IF NOT EXISTS idx_trn_accounting_guid
    ON tallypnl.trn_accounting(guid);
CREATE INDEX IF NOT EXISTS idx_trn_inventory_guid
    ON tallypnl.trn_inventory(guid);
CREATE INDEX IF NOT EXISTS idx_mst_stock_item_name
    ON tallypnl.mst_stock_item(name);


-- ###############################################################################
-- PART 2 — Stock, sales & purchase views (Company A → public)
-- ###############################################################################

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


-- ###############################################################################
-- PART 3 — Area-wise sales (Company A → public)
-- ###############################################################################

-- ─────────────────────────────────────────────────────────────────────────────
-- Area-wise sales — geocoding cache + party→area resolution + sales view
-- Company A (tallydb) only: it's the only schema with item-level trn_inventory
-- data (Company B / tallypnl has zero trn_inventory rows).
--
-- Resolution strategy (best available per party, populated by
-- app/scripts/geocode_parties.py — not derivable in pure SQL since it needs
-- an external geocoder):
--   1. mst_ledger.mailing_pincode  (~49% of parties)         -> precise
--   2. town extracted from mailing_address / party name       -> approximate
--   3. state centroid from trn_voucher.place_of_supply        -> coarse fallback
-- ─────────────────────────────────────────────────────────────────────────────

-- Raw geocoder result cache, keyed by whatever was looked up (pincode or town),
-- so re-running the script after a data sync doesn't re-hit Nominatim for
-- values it has already resolved.
CREATE TABLE IF NOT EXISTS public.geo_cache (
    query_key    varchar(256) PRIMARY KEY,   -- e.g. 'pincode:473001' or 'town:Guna|Madhya Pradesh'
    lat          numeric(9,6),
    lon          numeric(9,6),
    resolved_name varchar(256),
    source       varchar(32),                -- 'nominatim' | 'manual'
    resolved_at  timestamptz DEFAULT now()
);

-- Small hardcoded fallback for the states that actually appear in this data
-- (from trn_voucher.place_of_supply) — used only when a party has neither a
-- usable pincode nor an extractable town.
CREATE TABLE IF NOT EXISTS public.geo_state_centroid (
    state   varchar(128) PRIMARY KEY,
    lat     numeric(9,6) NOT NULL,
    lon     numeric(9,6) NOT NULL
);

INSERT INTO public.geo_state_centroid (state, lat, lon) VALUES
    ('Madhya Pradesh', 23.4734, 77.9479),
    ('Maharashtra', 19.7515, 75.7139),
    ('Rajasthan', 27.0238, 74.2179),
    ('Uttar Pradesh', 26.8467, 80.9462),
    ('Gujarat', 22.2587, 71.1924),
    ('Telangana', 18.1124, 79.0193),
    ('Chhattisgarh', 21.2787, 81.8661),
    ('Delhi', 28.7041, 77.1025),
    ('Haryana', 29.0588, 76.0856),
    ('Karnataka', 15.3173, 75.7139),
    ('Dadra & Nagar Haveli and Daman & Diu', 20.1809, 73.0169)
ON CONFLICT (state) DO NOTHING;

-- Final per-party resolution, one row per party_name, populated by
-- app/scripts/geocode_parties.py. area/resolution_level explain what the map
-- and drill-down UI actually show.
--
-- `area` is a human-readable rollup (city/town, or state as last resort) —
-- several pincodes within one city collapse to the same `area` so the map
-- doesn't fragment into dozens of bubbles per city. `pincode` keeps the raw
-- value alongside it (when known) so the sales team can still search/filter
-- at that finer grain without losing the city-level view.
CREATE TABLE IF NOT EXISTS public.party_area (
    party_name       varchar(1024) PRIMARY KEY,
    area             varchar(256) NOT NULL,   -- town/city rollup, or state as last resort
    pincode          varchar(16),             -- raw pincode when known, independent of `area`
    lat              numeric(9,6) NOT NULL,
    lon              numeric(9,6) NOT NULL,
    state            varchar(128),
    resolution_level varchar(16) NOT NULL,    -- 'pincode' | 'town' | 'state'
    resolved_at      timestamptz DEFAULT now()
);

ALTER TABLE public.party_area ADD COLUMN IF NOT EXISTS pincode varchar(16);

-- ─────────────────────────────────────────────
-- Monthly sales per party × item × resolved area — Company A
-- Same voucher/quantity filters as public.v_sales_monthly.
-- Dropped and recreated (not IF NOT EXISTS) so column changes like adding
-- `pincode` above always take effect when this file is re-run.
-- ─────────────────────────────────────────────
DROP MATERIALIZED VIEW IF EXISTS public.v_sales_by_area;

CREATE MATERIALIZED VIEW public.v_sales_by_area AS
SELECT
    DATE_TRUNC('month', v.date)::date   AS month,
    pa.area                             AS area,
    pa.pincode                          AS pincode,
    pa.lat                              AS lat,
    pa.lon                              AS lon,
    pa.state                            AS state,
    pa.resolution_level                 AS resolution_level,
    v.party_name                        AS party_name,
    i.item                              AS item,
    si.parent                           AS stock_group,
    SUM(ABS(i.quantity))                AS sold_qty,
    SUM(ABS(i.amount))                  AS sold_amount
FROM tallydb.trn_voucher v
JOIN tallydb.trn_inventory i        ON i.guid = v.guid
LEFT JOIN tallydb.mst_stock_item si ON si.name = i.item
JOIN public.party_area pa           ON pa.party_name = v.party_name
WHERE v.voucher_type IN (
        SELECT name FROM tallydb.mst_vouchertype WHERE parent = 'Sales'
    )
  AND i.quantity < 0
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_sales_by_area_uk
    ON public.v_sales_by_area (month, party_name, item);
CREATE INDEX IF NOT EXISTS idx_v_sales_by_area_area
    ON public.v_sales_by_area (area, month);
CREATE INDEX IF NOT EXISTS idx_v_sales_by_area_pincode
    ON public.v_sales_by_area (pincode, month);
CREATE INDEX IF NOT EXISTS idx_v_sales_by_area_party
    ON public.v_sales_by_area (party_name, month);
CREATE INDEX IF NOT EXISTS idx_v_sales_by_area_stock_group
    ON public.v_sales_by_area (stock_group, month);


-- ###############################################################################
-- PART 4 — Ledger analytics & P&L (Company B → tallypnl)
-- ###############################################################################

-- =============================================================================
-- Ledger Analytics & P&L  (schema: tallypnl / Company B)
-- Company B is a pure-accounting Tally company:
--   - No inventory tracking (trn_inventory = 0 rows)
--   - No bill-by-bill settlement (trn_bill = 1 row)
--   - All analytics derived from trn_accounting + mst_ledger
--
-- Sign convention in trn_accounting:
--   NEGATIVE amount = DEBIT  (e.g. customer debited on invoice → they owe us)
--   POSITIVE amount = CREDIT (e.g. customer credited on receipt → they paid)
--
-- tallypnl = Company B raw data + analytics
-- tallydb  = Company A  (used for COGS only)
-- =============================================================================

-- Drop existing views in dependency order before recreating
DROP VIEW          IF EXISTS tallypnl.v_b_aging_summary          CASCADE;
DROP MATERIALIZED VIEW IF EXISTS tallypnl.v_b_ledger_health      CASCADE;
DROP MATERIALIZED VIEW IF EXISTS tallypnl.v_b_ledger_summary     CASCADE;
DROP MATERIALIZED VIEW IF EXISTS tallypnl.v_b_invoice_activity   CASCADE;
DROP MATERIALIZED VIEW IF EXISTS tallypnl.v_b_customer_outstanding CASCADE;
DROP MATERIALIZED VIEW IF EXISTS tallypnl.v_b_sales_monthly      CASCADE;
DROP MATERIALIZED VIEW IF EXISTS tallypnl.v_b_payment_history    CASCADE;
DROP MATERIALIZED VIEW IF EXISTS tallypnl.v_b_outstanding_bills  CASCADE;
DROP VIEW          IF EXISTS tallypnl.v_pnl_monthly              CASCADE;


-- =============================================================================
-- SECTION 1 — Manual cost input tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS tallypnl.manual_costs (
    id          bigserial PRIMARY KEY,
    period      date           NOT NULL,        -- first of month: 2024-06-01
    cost_type   varchar(32)    NOT NULL,        -- 'transport' | 'labor' | 'other'
    amount      numeric(15,2)  NOT NULL,
    notes       varchar(512),
    created_at  timestamptz    DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_manual_costs_period_type
    ON tallypnl.manual_costs (period, cost_type);

-- Loan config: monthly interest = principal × monthly_rate_pct / 100  (simple, additive)
CREATE TABLE IF NOT EXISTS tallypnl.loan_config (
    id               bigserial PRIMARY KEY,
    loan_name        varchar(256)   NOT NULL,
    principal        numeric(15,2)  NOT NULL,
    monthly_rate_pct numeric(6,4)   NOT NULL,
    start_date       date           NOT NULL,
    end_date         date,
    notes            varchar(512),
    created_at       timestamptz    DEFAULT now()
);


-- =============================================================================
-- SECTION 2 — Monthly sales revenue (per customer, per month)
-- Source: trn_accounting entries for Sales Accounts group on INVOICE vouchers
-- Positive amount in trn_accounting = credit = revenue
-- =============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS tallypnl.v_b_sales_monthly AS
SELECT
    DATE_TRUNC('month', v.date)::date   AS month,
    v.party_name                        AS customer,
    SUM(ta.amount)                      AS sales_amount
FROM tallypnl.trn_voucher v
JOIN tallypnl.trn_accounting ta ON ta.guid = v.guid
JOIN tallypnl.mst_ledger ml     ON ml.name = ta.ledger
JOIN tallypnl.mst_group mg      ON mg.name = ml.parent
WHERE v.voucher_type = 'INVOICE'
  AND mg.primary_group = 'Sales Accounts'
GROUP BY 1, 2
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_b_sales_monthly_uk
    ON tallypnl.v_b_sales_monthly (month, customer);


-- =============================================================================
-- SECTION 3 — Customer outstanding balances
-- Source: mst_ledger.closing_balance (Tally computes this accurately)
-- Debtor groups: all mst_group rows with primary_group = 'Sundry Debtors'
-- This covers direct 'Sundry Debtors' members AND sub-groups like 'Hardware Debitors'
--
-- SIGN CONVENTION for mst_ledger.closing_balance:
--   NEGATIVE = Debit balance  → customer OWES US       (true receivable — include)
--   POSITIVE = Credit balance → WE OWE them            (advance/overpayment — exclude)
-- =============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS tallypnl.v_b_customer_outstanding AS
SELECT
    ml.name                                         AS customer,
    -ml.closing_balance                             AS outstanding_amount,   -- negate: Dr balance is stored negative; result is always positive
    COALESCE(ml.bill_credit_period, 30)             AS credit_days
FROM tallypnl.mst_ledger ml
JOIN tallypnl.mst_group mg ON mg.name = ml.parent
WHERE mg.primary_group = 'Sundry Debtors'
  AND ml.closing_balance != 0   -- include both Dr (they owe us) and Cr (we owe them) balances
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_b_customer_outstanding_uk
    ON tallypnl.v_b_customer_outstanding (customer);


-- =============================================================================
-- SECTION 4 — Invoice & receipt activity per customer
-- Identifies invoice dates and payment dates from trn_accounting
-- Using group membership (not party_name match) for robustness
-- =============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS tallypnl.v_b_invoice_activity AS
WITH invoice_entries AS (
    -- INVOICE vouchers: debtor ledger has NEGATIVE amount (debit = they owe us)
    SELECT
        ta.ledger                           AS customer,
        v.date                              AS txn_date,
        -ta.amount                          AS amount,      -- negate to get positive invoice value
        'invoice'::text                     AS txn_type
    FROM tallypnl.trn_voucher v
    JOIN tallypnl.trn_accounting ta ON ta.guid = v.guid
    JOIN tallypnl.mst_ledger ml     ON ml.name = ta.ledger
    JOIN tallypnl.mst_group mg      ON mg.name = ml.parent
    WHERE v.voucher_type = 'INVOICE'
      AND mg.primary_group = 'Sundry Debtors'
      AND ta.amount < 0                     -- debit entry only
),
receipt_entries AS (
    -- Receipt vouchers: debtor ledger has POSITIVE amount (credit = they paid)
    SELECT
        ta.ledger                           AS customer,
        v.date                              AS txn_date,
        ta.amount                           AS amount,      -- already positive
        'receipt'::text                     AS txn_type
    FROM tallypnl.trn_voucher v
    JOIN tallypnl.trn_accounting ta ON ta.guid = v.guid
    JOIN tallypnl.mst_vouchertype mvt ON mvt.name = v.voucher_type
    JOIN tallypnl.mst_ledger ml     ON ml.name = ta.ledger
    JOIN tallypnl.mst_group mg      ON mg.name = ml.parent
    WHERE mvt.parent = 'Receipt'
      AND mg.primary_group = 'Sundry Debtors'
      AND ta.amount > 0                     -- credit entry only
)
SELECT
    customer,
    MIN(CASE WHEN txn_type = 'invoice' THEN txn_date END)           AS first_invoice_date,
    MAX(CASE WHEN txn_type = 'invoice' THEN txn_date END)           AS last_invoice_date,
    COUNT(CASE WHEN txn_type = 'invoice' THEN 1 END)                AS total_invoices,
    SUM(CASE WHEN txn_type = 'invoice' THEN amount ELSE 0 END)      AS total_invoiced,
    MAX(CASE WHEN txn_type = 'receipt' THEN txn_date END)           AS last_receipt_date,
    COUNT(CASE WHEN txn_type = 'receipt' THEN 1 END)                AS total_receipts,
    SUM(CASE WHEN txn_type = 'receipt' THEN amount ELSE 0 END)      AS total_received
FROM (
    SELECT * FROM invoice_entries
    UNION ALL
    SELECT * FROM receipt_entries
) all_txns
GROUP BY customer
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_b_invoice_activity_uk
    ON tallypnl.v_b_invoice_activity (customer);


-- =============================================================================
-- SECTION 5 — Ledger summary (outstanding + activity + DSO estimate)
-- DSO estimate (ratio method): (outstanding / trailing 12M revenue) × 365
-- Overdue proxy: outstanding > 0 AND last invoice older than credit_days
-- =============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS tallypnl.v_b_ledger_summary AS
WITH ttm_revenue AS (
    SELECT customer, SUM(sales_amount) AS revenue_12m
    FROM tallypnl.v_b_sales_monthly
    WHERE month >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '12 months')::date
    GROUP BY customer
)
SELECT
    ob.customer,
    ob.outstanding_amount,
    ob.credit_days,
    ia.first_invoice_date,
    ia.last_invoice_date,
    ia.last_receipt_date,
    COALESCE(ia.total_invoices, 0)                                      AS total_invoices,
    COALESCE(ia.total_receipts, 0)                                      AS total_receipts,
    COALESCE(ia.total_invoiced, 0)                                      AS total_invoiced,
    COALESCE(ia.total_received, 0)                                      AS total_received,
    COALESCE(rv.revenue_12m, 0)                                         AS revenue_12m,

    -- DSO estimate via ratio method (only meaningful when customer owes us money)
    CASE WHEN ob.outstanding_amount > 0 AND COALESCE(rv.revenue_12m, 0) > 0
         THEN ROUND(ob.outstanding_amount / rv.revenue_12m * 365, 1)
         ELSE NULL END                                                  AS dso_estimate,

    -- Days since last invoice and last receipt
    COALESCE((CURRENT_DATE - ia.last_invoice_date)::int, 999)          AS days_since_last_invoice,
    COALESCE((CURRENT_DATE - ia.last_receipt_date)::int, 999)          AS days_since_last_receipt,

    -- Overdue proxy: outstanding > 0 AND no receipt in the last credit_period days
    -- Using receipt recency (not invoice date) because customers pay ad-hoc amounts
    -- that don't map 1:1 to invoices (underbilling, bank/cash payments).
    CASE WHEN ob.outstanding_amount > 0
              AND COALESCE((CURRENT_DATE - ia.last_receipt_date)::int, 999) > ob.credit_days
         THEN TRUE ELSE FALSE END                                       AS has_overdue

FROM tallypnl.v_b_customer_outstanding ob
LEFT JOIN tallypnl.v_b_invoice_activity ia ON ia.customer = ob.customer
LEFT JOIN ttm_revenue rv                    ON rv.customer = ob.customer
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_b_ledger_summary_uk
    ON tallypnl.v_b_ledger_summary (customer);


-- =============================================================================
-- SECTION 6 — Ledger health score (0–100)
-- Score bands: ≥ 70 green | 40–69 amber | < 40 red
--
-- Components:
--   DSO score      30 pts — ≤60d=30pts (good), 135d=15pts (4.5mo avg), ≥210d=0pts
--   Overdue flag   25 pts — 25 if current (paid within credit terms), 0 if overdue
--   Recency        20 pts — days since last receipt (full if < 30 days, zero at 90+)
--   Engagement     15 pts — number of receipts received (customer activity)
--   Balance ratio  10 pts — outstanding vs total invoiced (low residual = better)
-- =============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS tallypnl.v_b_ledger_health AS
SELECT
    ls.customer,
    ls.outstanding_amount,
    ls.credit_days,
    ls.dso_estimate,
    ls.revenue_12m,
    ls.last_invoice_date,
    ls.last_receipt_date,
    ls.days_since_last_receipt,
    ls.has_overdue,
    ls.total_invoices,
    ls.total_receipts,
    ls.total_invoiced,
    ls.total_received,

    -- ── Aging metrics ─────────────────────────────────────────────────────────
    GREATEST(0, ls.days_since_last_receipt - ls.credit_days)                        AS overdue_days,

    CASE
        WHEN ls.outstanding_amount <= 0                                              THEN 'credit'
        WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) = 0          THEN 'current'
        WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) <= 30        THEN '1_30'
        WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) <= 60        THEN '31_60'
        ELSE                                                                              '60plus'
    END                                                                             AS aging_bucket,

    -- ── Component scores ─────────────────────────────────────────────────────

    -- DSO score (30 pts): ≤60d=30pts, 135d=15pts (4.5mo avg), ≥210d=0pts — linear scale 60→210
    ROUND(GREATEST(0, LEAST(30,
        CASE WHEN ls.dso_estimate IS NOT NULL AND ls.dso_estimate > 0
             THEN 30.0 * GREATEST(0, 210 - ls.dso_estimate) / 150.0
             ELSE 15 END
    )), 1)                                                      AS score_dso,

    -- Aging score (25 pts): graduated by bucket — replaces binary overdue flag
    --   credit / current → 25 (full score) | 1-30d → 15 | 31-60d → 6 | 60d+ → 0
    CASE
        WHEN ls.outstanding_amount <= 0                                               THEN 25.0
        WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) = 0           THEN 25.0
        WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) <= 30         THEN 15.0
        WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) <= 60         THEN 6.0
        ELSE                                                                               0.0
    END                                                                              AS score_aging,

    -- Recency score (20 pts): calibrated to credit terms — full if within terms, zero at 60d overdue
    ROUND(GREATEST(0, LEAST(20,
        20.0 * GREATEST(0, 60.0 - GREATEST(0, ls.days_since_last_receipt - ls.credit_days)) / 60.0
    )), 1)                                                      AS score_recency,

    -- Engagement score (15 pts): 1.5 pts per receipt, capped at 15
    ROUND(LEAST(15.0, ls.total_receipts * 1.5), 1)             AS score_engagement,

    -- Balance ratio score (10 pts): full if outstanding < 20% of total invoiced
    ROUND(GREATEST(0, LEAST(10,
        CASE WHEN COALESCE(ls.total_invoiced, 0) > 0
             THEN 10.0 * GREATEST(0, 1 - ls.outstanding_amount / (ls.total_invoiced * 0.5))
             ELSE 5 END
    )), 1)                                                      AS score_balance_ratio,

    -- ── Composite ────────────────────────────────────────────────────────────
    ROUND(
        GREATEST(0, LEAST(30,
            CASE WHEN ls.dso_estimate IS NOT NULL AND ls.dso_estimate > 0
                 THEN 30.0 * GREATEST(0, 210 - ls.dso_estimate) / 150.0
                 ELSE 15 END))
        + CASE
            WHEN ls.outstanding_amount <= 0                                               THEN 25.0
            WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) = 0           THEN 25.0
            WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) <= 30         THEN 15.0
            WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) <= 60         THEN 6.0
            ELSE                                                                               0.0
          END
        + GREATEST(0, LEAST(20,
            20.0 * GREATEST(0, 60.0 - GREATEST(0, ls.days_since_last_receipt - ls.credit_days)) / 60.0))
        + LEAST(15.0, ls.total_receipts * 1.5)
        + GREATEST(0, LEAST(10,
            CASE WHEN COALESCE(ls.total_invoiced, 0) > 0
                 THEN 10.0 * GREATEST(0, 1 - ls.outstanding_amount / (ls.total_invoiced * 0.5))
                 ELSE 5 END))
    , 1)                                                        AS health_score,

    CASE
        WHEN ROUND(
            GREATEST(0, LEAST(30,
                CASE WHEN ls.dso_estimate IS NOT NULL AND ls.dso_estimate > 0
                     THEN 30.0 * GREATEST(0, 210 - ls.dso_estimate) / 150.0
                     ELSE 15 END))
            + CASE
                WHEN ls.outstanding_amount <= 0                                               THEN 25.0
                WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) = 0           THEN 25.0
                WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) <= 30         THEN 15.0
                WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) <= 60         THEN 6.0
                ELSE                                                                               0.0
              END
            + GREATEST(0, LEAST(20,
                20.0 * GREATEST(0, 60.0 - GREATEST(0, ls.days_since_last_receipt - ls.credit_days)) / 60.0))
            + LEAST(15.0, ls.total_receipts * 1.5)
            + GREATEST(0, LEAST(10,
                CASE WHEN COALESCE(ls.total_invoiced, 0) > 0
                     THEN 10.0 * GREATEST(0, 1 - ls.outstanding_amount / (ls.total_invoiced * 0.5))
                     ELSE 5 END))
        , 1) >= 70 THEN 'green'
        WHEN ROUND(
            GREATEST(0, LEAST(30,
                CASE WHEN ls.dso_estimate IS NOT NULL AND ls.dso_estimate > 0
                     THEN 30.0 * GREATEST(0, 210 - ls.dso_estimate) / 150.0
                     ELSE 15 END))
            + CASE
                WHEN ls.outstanding_amount <= 0                                               THEN 25.0
                WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) = 0           THEN 25.0
                WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) <= 30         THEN 15.0
                WHEN GREATEST(0, ls.days_since_last_receipt - ls.credit_days) <= 60         THEN 6.0
                ELSE                                                                               0.0
              END
            + GREATEST(0, LEAST(20,
                20.0 * GREATEST(0, 60.0 - GREATEST(0, ls.days_since_last_receipt - ls.credit_days)) / 60.0))
            + LEAST(15.0, ls.total_receipts * 1.5)
            + GREATEST(0, LEAST(10,
                CASE WHEN COALESCE(ls.total_invoiced, 0) > 0
                     THEN 10.0 * GREATEST(0, 1 - ls.outstanding_amount / (ls.total_invoiced * 0.5))
                     ELSE 5 END))
        , 1) >= 40 THEN 'amber'
        ELSE 'red'
    END                                                         AS health_rag

FROM tallypnl.v_b_ledger_summary ls
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_b_ledger_health_uk
    ON tallypnl.v_b_ledger_health (customer);


-- =============================================================================
-- SECTION 7 — Aging summary (regular view — always current from latest MV)
-- Aggregates outstanding AR by aging bucket and computes ADD / Best Possible DSO
--
-- Buckets (based on overdue_days = days_since_last_receipt - credit_days):
--   credit   — customer has credit balance (we owe them)
--   current  — outstanding but not yet overdue
--   1_30     — 1-30 days past due
--   31_60    — 31-60 days past due
--   60plus   — more than 60 days past due
-- =============================================================================

CREATE OR REPLACE VIEW tallypnl.v_b_aging_summary AS
WITH buckets AS (
    SELECT
        SUM(GREATEST(outstanding_amount, 0))                                            AS total_receivable,
        SUM(CASE WHEN aging_bucket = 'current' THEN outstanding_amount  ELSE 0 END)    AS current_ar,
        SUM(CASE WHEN aging_bucket = '1_30'    THEN outstanding_amount  ELSE 0 END)    AS overdue_1_30,
        SUM(CASE WHEN aging_bucket = '31_60'   THEN outstanding_amount  ELSE 0 END)    AS overdue_31_60,
        SUM(CASE WHEN aging_bucket = '60plus'  THEN outstanding_amount  ELSE 0 END)    AS overdue_60plus,
        SUM(CASE WHEN outstanding_amount < 0   THEN -outstanding_amount ELSE 0 END)    AS credit_balance,
        COUNT(CASE WHEN aging_bucket = 'current' THEN 1 END)                           AS current_count,
        COUNT(CASE WHEN aging_bucket = '1_30'    THEN 1 END)                           AS overdue_1_30_count,
        COUNT(CASE WHEN aging_bucket = '31_60'   THEN 1 END)                           AS overdue_31_60_count,
        COUNT(CASE WHEN aging_bucket = '60plus'  THEN 1 END)                           AS overdue_60plus_count,
        COUNT(CASE WHEN outstanding_amount < 0   THEN 1 END)                           AS credit_count,
        SUM(COALESCE(revenue_12m, 0))                                                  AS total_revenue_12m
    FROM tallypnl.v_b_ledger_health
)
SELECT
    total_receivable,
    current_ar,
    overdue_1_30,
    overdue_31_60,
    overdue_60plus,
    credit_balance,
    current_count,
    overdue_1_30_count,
    overdue_31_60_count,
    overdue_60plus_count,
    credit_count,
    total_revenue_12m,

    -- Portfolio DSO: total receivable vs 12-month revenue (annualised)
    CASE WHEN total_revenue_12m > 0
         THEN ROUND(total_receivable / total_revenue_12m * 365, 1)
         ELSE NULL END                                                                  AS portfolio_dso,

    -- Best Possible DSO: only the not-yet-overdue portion of AR
    CASE WHEN total_revenue_12m > 0
         THEN ROUND(current_ar / total_revenue_12m * 365, 1)
         ELSE NULL END                                                                  AS best_possible_dso,

    -- ADD = Portfolio DSO − Best Possible DSO (days lost to late payment)
    CASE WHEN total_revenue_12m > 0
         THEN ROUND((total_receivable - current_ar) / total_revenue_12m * 365, 1)
         ELSE NULL END                                                                  AS add_days

FROM buckets;


-- =============================================================================
-- SECTION 8 — P&L monthly (regular view — always current)
-- Revenue  : tallypnl trn_accounting (Sales Accounts on INVOICE vouchers)
-- COGS     : tallydb trn_inventory (Company A purchases)
-- Fixed    : tallypnl.manual_costs
-- Loans    : tallypnl.loan_config (principal × monthly_rate_pct / 100)
-- =============================================================================

CREATE OR REPLACE VIEW tallypnl.v_pnl_monthly AS
WITH months AS (
    SELECT DISTINCT DATE_TRUNC('month', date)::date AS month
    FROM tallypnl.trn_voucher
    UNION
    SELECT DISTINCT DATE_TRUNC('month', date)::date AS month
    FROM tallydb.trn_voucher
),
revenue AS (
    SELECT
        DATE_TRUNC('month', v.date)::date   AS month,
        SUM(ta.amount)                      AS revenue
    FROM tallypnl.trn_voucher v
    JOIN tallypnl.trn_accounting ta ON ta.guid = v.guid
    JOIN tallypnl.mst_ledger ml     ON ml.name = ta.ledger
    JOIN tallypnl.mst_group mg      ON mg.name = ml.parent
    WHERE v.voucher_type = 'INVOICE'
      AND mg.primary_group = 'Sales Accounts'
    GROUP BY 1
),
cogs AS (
    SELECT
        DATE_TRUNC('month', v.date)::date   AS month,
        SUM(ABS(i.amount))                  AS cogs
    FROM tallydb.trn_voucher v
    JOIN tallydb.trn_inventory i ON i.guid = v.guid
    WHERE v.voucher_type IN (
        SELECT name FROM tallydb.mst_vouchertype WHERE parent = 'Purchase'
    )
    AND i.quantity > 0
    GROUP BY 1
),
fixed_costs AS (
    SELECT period AS month, SUM(amount) AS total_fixed
    FROM tallypnl.manual_costs
    GROUP BY 1
),
loan_costs AS (
    SELECT
        m.month,
        COALESCE(SUM(lc.principal * lc.monthly_rate_pct / 100.0), 0) AS total_loan_interest
    FROM months m
    CROSS JOIN tallypnl.loan_config lc
    WHERE lc.start_date <= m.month
      AND (lc.end_date IS NULL OR lc.end_date >= m.month)
    GROUP BY 1
)
SELECT
    m.month,
    COALESCE(r.revenue, 0)                                              AS revenue,
    COALESCE(c.cogs, 0)                                                 AS cogs,
    COALESCE(r.revenue, 0) - COALESCE(c.cogs, 0)                       AS gross_profit,
    ROUND(100.0 * (COALESCE(r.revenue, 0) - COALESCE(c.cogs, 0))
          / NULLIF(COALESCE(r.revenue, 0), 0), 2)                       AS gross_margin_pct,
    COALESCE(f.total_fixed, 0)                                          AS fixed_costs,
    COALESCE(l.total_loan_interest, 0)                                  AS loan_interest,
    COALESCE(f.total_fixed, 0) + COALESCE(l.total_loan_interest, 0)    AS total_overhead,
    COALESCE(r.revenue, 0)
        - COALESCE(c.cogs, 0)
        - COALESCE(f.total_fixed, 0)
        - COALESCE(l.total_loan_interest, 0)                            AS net_profit,
    ROUND(100.0 * (
        COALESCE(r.revenue, 0)
        - COALESCE(c.cogs, 0)
        - COALESCE(f.total_fixed, 0)
        - COALESCE(l.total_loan_interest, 0)
    ) / NULLIF(COALESCE(r.revenue, 0), 0), 2)                           AS net_margin_pct
FROM months m
LEFT JOIN revenue     r ON r.month = m.month
LEFT JOIN cogs        c ON c.month = m.month
LEFT JOIN fixed_costs f ON f.month = m.month
LEFT JOIN loan_costs  l ON l.month = m.month
ORDER BY m.month;


-- ###############################################################################
-- PART 5 — Refresh (run after every data sync, in this order)
-- ###############################################################################
-- Run these on their own — not as part of the setup above.
--
-- Company A (tallydb → public)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_current_stock;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_sales_monthly;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_sales_by_group;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_purchase_by_group;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_top_moving_items;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_sales_by_area;   -- also after running geocode_parties.py
--
-- Company B (tallypnl) — plain REFRESH: these are created WITH NO DATA, and
-- CONCURRENTLY fails on a never-populated view
-- REFRESH MATERIALIZED VIEW tallypnl.v_b_sales_monthly;
-- REFRESH MATERIALIZED VIEW tallypnl.v_b_customer_outstanding;
-- REFRESH MATERIALIZED VIEW tallypnl.v_b_invoice_activity;
-- REFRESH MATERIALIZED VIEW tallypnl.v_b_ledger_summary;
-- REFRESH MATERIALIZED VIEW tallypnl.v_b_ledger_health;
--
-- Regular views — always current, no refresh needed:
--   public.v_reorder_alerts, tallypnl.v_b_aging_summary, tallypnl.v_pnl_monthly
--
-- After refreshing, press "Run Forecast" in the app to rebuild stock_forecast.


-- =============================================================================
-- SECTION 9 — Diagnostics (run these to verify sign convention is correct)
-- =============================================================================

-- Q1: Shows ALL Sundry Debtor ledgers with their balance direction.
--     "receivable" = they owe us (Dr balance, closing_balance < 0) → included in health
--     "advance"    = we owe them (Cr balance, closing_balance > 0) → excluded from health
-- SELECT
--     ml.name,
--     ml.parent,
--     ml.closing_balance,
--     CASE WHEN ml.closing_balance < 0 THEN 'receivable (they owe us)'
--          WHEN ml.closing_balance > 0 THEN 'advance (we owe them)'
--          ELSE 'settled' END AS balance_direction,
--     ABS(ml.closing_balance) AS balance_abs
-- FROM tallypnl.mst_ledger ml
-- JOIN tallypnl.mst_group mg ON mg.name = ml.parent
-- WHERE mg.primary_group = 'Sundry Debtors'
-- ORDER BY ml.closing_balance ASC;

-- Q2: Revenue sanity check — confirm Sales Accounts credits are positive
-- SELECT SUM(ta.amount) AS total_revenue
-- FROM tallypnl.trn_voucher v
-- JOIN tallypnl.trn_accounting ta ON ta.guid = v.guid
-- JOIN tallypnl.mst_ledger ml ON ml.name = ta.ledger
-- JOIN tallypnl.mst_group mg ON mg.name = ml.parent
-- WHERE v.voucher_type = 'INVOICE' AND mg.primary_group = 'Sales Accounts';

-- Q3: Invoice activity sanity — spot check one customer
-- SELECT ta.ledger, v.voucher_type, v.date, ta.amount
-- FROM tallypnl.trn_accounting ta
-- JOIN tallypnl.trn_voucher v ON v.guid = ta.guid
-- JOIN tallypnl.mst_ledger ml ON ml.name = ta.ledger
-- JOIN tallypnl.mst_group mg ON mg.name = ml.parent
-- WHERE mg.primary_group = 'Sundry Debtors'
-- ORDER BY v.date DESC LIMIT 20;
