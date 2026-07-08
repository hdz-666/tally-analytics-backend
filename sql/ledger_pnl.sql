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
  AND ml.closing_balance < 0    -- NEGATIVE = Debit balance = they owe us (receivable)
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

    -- DSO estimate via ratio method
    CASE WHEN COALESCE(rv.revenue_12m, 0) > 0
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

    -- ── Component scores ─────────────────────────────────────────────────────

    -- DSO score (30 pts): ≤60d=30pts, 135d=15pts (4.5mo avg), ≥210d=0pts — linear scale 60→210
    ROUND(GREATEST(0, LEAST(30,
        CASE WHEN ls.dso_estimate IS NOT NULL AND ls.dso_estimate > 0
             THEN 30.0 * GREATEST(0, 210 - ls.dso_estimate) / 150.0
             ELSE 15 END
    )), 1)                                                      AS score_dso,

    -- Overdue score (25 pts): binary — 25 if not overdue, 0 if overdue
    CASE WHEN ls.has_overdue THEN 0.0 ELSE 25.0 END            AS score_overdue,

    -- Recency score (20 pts): full if last receipt within 30 days, zero at 90+ days
    ROUND(GREATEST(0, LEAST(20,
        20.0 * GREATEST(0, 90 - ls.days_since_last_receipt) / 90.0
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
                 THEN 30.0 * ls.credit_days / ls.dso_estimate ELSE 15 END))
        + CASE WHEN ls.has_overdue THEN 0.0 ELSE 25.0 END
        + GREATEST(0, LEAST(20,
            20.0 * GREATEST(0, 90 - ls.days_since_last_receipt) / 90.0))
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
                     THEN 30.0 * ls.credit_days / ls.dso_estimate ELSE 15 END))
            + CASE WHEN ls.has_overdue THEN 0.0 ELSE 25.0 END
            + GREATEST(0, LEAST(20,
                20.0 * GREATEST(0, 90 - ls.days_since_last_receipt) / 90.0))
            + LEAST(15.0, ls.total_receipts * 1.5)
            + GREATEST(0, LEAST(10,
                CASE WHEN COALESCE(ls.total_invoiced, 0) > 0
                     THEN 10.0 * GREATEST(0, 1 - ls.outstanding_amount / (ls.total_invoiced * 0.5))
                     ELSE 5 END))
        , 1) >= 70 THEN 'green'
        WHEN ROUND(
            GREATEST(0, LEAST(30,
                CASE WHEN ls.dso_estimate IS NOT NULL AND ls.dso_estimate > 0
                     THEN 30.0 * ls.credit_days / ls.dso_estimate ELSE 15 END))
            + CASE WHEN ls.has_overdue THEN 0.0 ELSE 25.0 END
            + GREATEST(0, LEAST(20,
                20.0 * GREATEST(0, 90 - ls.days_since_last_receipt) / 90.0))
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
-- SECTION 7 — P&L monthly (regular view — always current)
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


-- =============================================================================
-- SECTION 8 — Refresh order (run after each Company B data sync)
-- =============================================================================
-- REFRESH MATERIALIZED VIEW tallypnl.v_b_sales_monthly;
-- REFRESH MATERIALIZED VIEW tallypnl.v_b_customer_outstanding;
-- REFRESH MATERIALIZED VIEW tallypnl.v_b_invoice_activity;
-- REFRESH MATERIALIZED VIEW tallypnl.v_b_ledger_summary;
-- REFRESH MATERIALIZED VIEW tallypnl.v_b_ledger_health;
-- v_pnl_monthly is a regular VIEW — no refresh needed


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
