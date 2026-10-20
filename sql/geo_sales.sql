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

-- ─────────────────────────────────────────────
-- Refresh after each monthly sync AND after re-running geocode_parties.py
-- ─────────────────────────────────────────────
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.v_sales_by_area;
