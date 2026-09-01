"""
One-time (re-runnable) job that resolves an approximate area — town, or state
as a last resort — for every party that appears on a Company A sales voucher,
and writes the result to public.party_area.

Resolution order per party:
    1. mst_ledger.mailing_pincode                        -> 'pincode'
    2. town extracted from mailing_address / party name   -> 'town'
    3. state centroid (mailing_state, or the most common
       trn_voucher.place_of_supply for that party)         -> 'state'

Geocoding uses OpenStreetMap Nominatim. Every lookup is cached in
public.geo_cache keyed by the query, so re-running this after a data sync
only geocodes pincodes/towns it hasn't seen before — safe to re-run anytime.

Run from the backend root:
    .venv/Scripts/python.exe -m app.scripts.geocode_parties
"""

import asyncio
import re
from collections import Counter

import asyncpg
import httpx

from app.core.config import settings

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = (
    "tally-analytics-area-sales/1.0 (contact: swapnayhardik@gmail.com)"
)
REQUEST_DELAY_SECONDS = 1.1  # Nominatim usage policy: max 1 request/sec

GENERIC_TOKENS = {
    "LTD", "PVT", "LIMITED", "AND", "CO", "COMPANY", "INDIA", "GST", "NIL",
    "H/W", "HARDWARE", "PLYWOOD", "TRADING", "ENTERPRISES", "STORE", "STORES",
    "HOUSE", "CENTER", "CENTRE", "MARKET", "ROAD", "COLONY", "SHOP", "AGENCY",
    "AGENCIES", "SUPPLIERS", "DISTRIBUTORS", "TIMBER", "TIMBERS", "DECOR",
    "DECORE", "SALES", "CORPORATION", "BROTHERS", "SON", "SONS", "NA",
}

ADMIN_UNIT_MARKERS = ("TAHSIL", "TALUKA", "SUBDISTRICT", "WARD", "ZONE")


def clean_token(tok: str) -> str:
    tok = re.sub(r"\d{4,}", "", tok)  # strip phone numbers / pincodes
    tok = re.sub(r"[^A-Za-z\s]", " ", tok)
    return re.sub(r"\s+", " ", tok).strip()


def extract_town(address: str | None, party_name: str | None) -> str | None:
    if address:
        for raw in reversed(address.split(",")):
            cleaned = clean_token(raw)
            if len(cleaned) >= 3 and cleaned.upper() not in GENERIC_TOKENS:
                return cleaned.title()
    if party_name:
        words = [clean_token(w) for w in party_name.split()]
        for w in reversed(words):
            if len(w) >= 3 and w.upper() not in GENERIC_TOKENS:
                return w.title()
    return None


def city_from_display_name(display_name: str | None, fallback: str) -> str:
    """Turn a Nominatim pincode result's display_name (most-specific first)
    into a readable city/district label, e.g.
    '452001, Rau, Indore, Madhya Pradesh, India' -> 'Indore'. Falls back to
    the raw pincode if nothing usable survives filtering admin units.
    """
    if not display_name:
        return fallback
    tokens = [t.strip() for t in display_name.split(",")]
    tokens = tokens[:-2] if len(tokens) > 2 else tokens  # drop state, country
    candidates = [
        t for t in tokens
        if t and not t.isdigit()
        and not any(marker in t.upper() for marker in ADMIN_UNIT_MARKERS)
    ]
    return candidates[-1] if candidates else fallback


async def geocode(
    client: httpx.AsyncClient, params: dict
) -> tuple[float, float, str] | None:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            resp = await client.get(
                NOMINATIM_URL,
                params={**params, "format": "json", "limit": 1},
                headers={"User-Agent": USER_AGENT},
                timeout=30,
            )
            resp.raise_for_status()
            results = resp.json()
            if not results:
                return None
            r = results[0]
            return float(r["lat"]), float(r["lon"]), r.get("display_name", "")
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
            print(f"  ...geocode retry {attempt + 1}/3 after {exc!r}")
            await asyncio.sleep(REQUEST_DELAY_SECONDS * (attempt + 1))
    print(f"  ...giving up on {params!r}: {last_error!r}")
    return None


async def get_cached_or_geocode(
    conn: asyncpg.Connection,
    client: httpx.AsyncClient,
    query_key: str,
    params: dict,
    cache: dict,
) -> tuple[float, float, str] | None:
    if query_key in cache:
        return cache[query_key]

    geocoded = await geocode(client, params)
    await asyncio.sleep(REQUEST_DELAY_SECONDS)

    if geocoded is None:
        # Cache the miss too (lat/lon left NULL) — otherwise every re-run
        # retries the same unresolvable pincode/town against Nominatim.
        await conn.execute(
            """
            INSERT INTO public.geo_cache (query_key, source)
            VALUES ($1, 'nominatim')
            ON CONFLICT (query_key) DO NOTHING
            """,
            query_key,
        )
        cache[query_key] = None
        return None

    lat, lon, display_name = geocoded
    await conn.execute(
        """
        INSERT INTO public.geo_cache
            (query_key, lat, lon, resolved_name, source)
        VALUES ($1, $2, $3, $4, 'nominatim')
        ON CONFLICT (query_key) DO NOTHING
        """,
        query_key, lat, lon, display_name,
    )
    result = (lat, lon, display_name)
    cache[query_key] = result
    return result


async def main():
    conn = await asyncpg.connect(settings.database_url)

    # Preload the whole cache once instead of one round-trip per party — with
    # ~1,400 parties this turns a multi-minute run (mostly waiting on the
    # Supabase pooler's latency) into a few seconds when nothing is new.
    cache: dict = {
        r["query_key"]: (
            (float(r["lat"]), float(r["lon"]), r["resolved_name"] or "")
            if r["lat"] is not None
            else None  # a previously confirmed miss — don't retry it
        )
        for r in await conn.fetch(
            "SELECT query_key, lat, lon, resolved_name FROM public.geo_cache"
        )
    }

    parties = await conn.fetch(
        """
        SELECT DISTINCT v.party_name
        FROM tallydb.trn_voucher v
        JOIN tallydb.trn_inventory i ON i.guid = v.guid
        WHERE v.voucher_type IN (
                SELECT name FROM tallydb.mst_vouchertype
                WHERE parent = 'Sales'
              )
          AND i.quantity < 0
          AND v.party_name IS NOT NULL AND v.party_name != ''
        """
    )
    party_names = [p["party_name"] for p in parties]
    print(f"{len(party_names)} distinct parties with sales to resolve")

    ledgers = {
        r["name"]: r
        for r in await conn.fetch(
            """
            SELECT name, mailing_address, mailing_state, mailing_pincode
            FROM tallydb.mst_ledger
            """
        )
    }

    fallback_state_rows = await conn.fetch(
        """
        SELECT party_name, place_of_supply, COUNT(*) AS n
        FROM tallydb.trn_voucher
        WHERE party_name = ANY($1)
          AND place_of_supply IS NOT NULL AND place_of_supply != ''
        GROUP BY party_name, place_of_supply
        """,
        party_names,
    )
    fallback_state: dict[str, str] = {}
    counters: dict[str, Counter] = {}
    for r in fallback_state_rows:
        counter = counters.setdefault(r["party_name"], Counter())
        counter[r["place_of_supply"]] = r["n"]
    for party, counter in counters.items():
        fallback_state[party] = counter.most_common(1)[0][0]

    state_centroids = {
        r["state"]: (float(r["lat"]), float(r["lon"]))
        for r in await conn.fetch(
            "SELECT state, lat, lon FROM public.geo_state_centroid"
        )
    }

    resolved = 0
    counts = Counter()
    rows_to_upsert: list[tuple] = []

    async with httpx.AsyncClient() as client:
        for party in party_names:
            ledger = ledgers.get(party)
            pincode = (
                (ledger["mailing_pincode"] or "").strip() if ledger else ""
            )
            address = (
                (ledger["mailing_address"] or "").strip() if ledger else ""
            )
            mailing_state = (
                (ledger["mailing_state"] or "").strip() if ledger else ""
            )
            state = mailing_state or fallback_state.get(party, "")
            # Kept alongside `area` (which rolls pincodes up to a city) so
            # the sales team can still search/filter at pincode precision.
            raw_pincode = pincode if re.fullmatch(r"\d{6}", pincode) else None

            area = lat = lon = level = None

            if re.fullmatch(r"\d{6}", pincode):
                coords = await get_cached_or_geocode(
                    conn, client, f"pincode:{pincode}",
                    {"postalcode": pincode, "country": "India"}, cache,
                )
                if coords:
                    lat, lon, display_name = coords
                    area = city_from_display_name(
                        display_name, fallback=pincode
                    )
                    level = "pincode"

            if lat is None:
                town = extract_town(address, party)
                if town:
                    query_key = f"town:{town}|{state}"
                    coords = await get_cached_or_geocode(
                        conn, client, query_key,
                        {"city": town, "state": state, "country": "India"},
                        cache,
                    )
                    if coords:
                        lat, lon, _ = coords
                        area = town
                        level = "town"

            if lat is None and state and state in state_centroids:
                lat, lon = state_centroids[state]
                area = state
                level = "state"

            if lat is None:
                counts["unresolved"] += 1
                continue

            rows_to_upsert.append(
                (party, area, raw_pincode, lat, lon, state or None, level)
            )
            resolved += 1
            counts[level] += 1

            if resolved % 50 == 0:
                print(f"...{resolved}/{len(party_names)} resolved")

    # One bulk upsert instead of one round-trip per party — with ~1,400
    # parties and a remote DB, per-row awaits dominate wall time far more
    # than the geocoding itself once the cache is warm.
    if rows_to_upsert:
        columns = list(zip(*rows_to_upsert))
        await conn.execute(
            """
            INSERT INTO public.party_area
                (party_name, area, pincode, lat, lon, state,
                 resolution_level)
            SELECT * FROM unnest(
                $1::varchar(1024)[], $2::varchar(256)[], $3::varchar(16)[],
                $4::numeric[], $5::numeric[],
                $6::varchar(128)[], $7::varchar(16)[]
            )
            ON CONFLICT (party_name) DO UPDATE
                SET area = EXCLUDED.area,
                    pincode = EXCLUDED.pincode,
                    lat = EXCLUDED.lat,
                    lon = EXCLUDED.lon,
                    state = EXCLUDED.state,
                    resolution_level = EXCLUDED.resolution_level,
                    resolved_at = now()
            """,
            *columns,
        )

    print(f"\nDone. Resolved {resolved}/{len(party_names)} parties.")
    for level, n in counts.most_common():
        print(f"  {level}: {n}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
