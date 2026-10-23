from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.scripts import geocode_parties as gp
from tests.conftest import MockConnection


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("app.scripts.geocode_parties.asyncio.sleep", AsyncMock()) as m:
        yield m


def client_with(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# ── clean_token ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("  Indore  ", "Indore"),
        ("Indore-452001", "Indore"),
        ("Ph: 9876543210", "Ph"),
        ("M.G. Road", "M G Road"),
        ("1234", ""),
    ],
)
def test_clean_token(raw, expected):
    assert gp.clean_token(raw) == expected


# ── extract_town ─────────────────────────────────────────────────────────────

def test_extract_town_uses_last_address_part():
    assert gp.extract_town("12, MG Road, Indore", None) == "Indore"


def test_extract_town_skips_pincode_and_generic_parts():
    assert gp.extract_town("Shop 4, Bhopal, India, 462001", None) == "Bhopal"


def test_extract_town_falls_back_to_party_name():
    assert gp.extract_town(None, "Sharma Hardware Ujjain") == "Ujjain"


def test_extract_town_party_name_skips_generic_words():
    assert gp.extract_town("", "Gupta Timber Pvt Ltd") == "Gupta"


def test_extract_town_returns_none_when_nothing_usable():
    assert gp.extract_town("12, 34", "AB Co") is None
    assert gp.extract_town(None, None) is None


# ── city_from_display_name ───────────────────────────────────────────────────

def test_city_from_display_name_picks_city():
    name = "452001, Rau, Indore, Madhya Pradesh, India"
    assert gp.city_from_display_name(name, "452001") == "Indore"


def test_city_from_display_name_skips_admin_units():
    name = "452001, Indore, Indore Tahsil, Madhya Pradesh, India"
    assert gp.city_from_display_name(name, "452001") == "Indore"


def test_city_from_display_name_fallbacks():
    assert gp.city_from_display_name(None, "452001") == "452001"
    assert gp.city_from_display_name("", "452001") == "452001"
    assert gp.city_from_display_name("452001, Madhya Pradesh, India", "452001") == "452001"


# ── geocode ──────────────────────────────────────────────────────────────────

async def test_geocode_success_sends_policy_headers():
    seen = {}

    def handler(request: httpx.Request):
        seen["params"] = dict(request.url.params)
        seen["ua"] = request.headers["User-Agent"]
        return httpx.Response(200, json=[{"lat": "22.7", "lon": "75.8", "display_name": "Indore"}])

    async with client_with(handler) as client:
        result = await gp.geocode(client, {"postalcode": "452001"})

    assert result == (22.7, 75.8, "Indore")
    assert seen["params"] == {"postalcode": "452001", "format": "json", "limit": "1"}
    assert seen["ua"] == gp.USER_AGENT


async def test_geocode_no_results_returns_none():
    async with client_with(lambda r: httpx.Response(200, json=[])) as client:
        assert await gp.geocode(client, {"q": "nowhere"}) is None


async def test_geocode_retries_transport_errors_then_succeeds(no_sleep):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.ConnectError("down")
        return httpx.Response(200, json=[{"lat": "1", "lon": "2"}])

    async with client_with(handler) as client:
        assert await gp.geocode(client, {"q": "x"}) == (1.0, 2.0, "")
    assert calls["n"] == 3
    assert no_sleep.await_count == 2


async def test_geocode_gives_up_after_three_attempts():
    def handler(request):
        raise httpx.ReadTimeout("slow")

    async with client_with(handler) as client:
        assert await gp.geocode(client, {"q": "x"}) is None


async def test_geocode_http_error_raises():
    async with client_with(lambda r: httpx.Response(500)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await gp.geocode(client, {"q": "x"})


# ── get_cached_or_geocode ────────────────────────────────────────────────────

async def test_cache_hit_skips_network_and_db():
    conn = MockConnection()
    cache = {"pin:452001": (1.0, 2.0, "Indore")}
    with patch.object(gp, "geocode", AsyncMock()) as geo:
        result = await gp.get_cached_or_geocode(conn, None, "pin:452001", {}, cache)
    assert result == (1.0, 2.0, "Indore")
    geo.assert_not_called()
    conn.execute.assert_not_called()


async def test_cached_miss_is_not_retried():
    conn = MockConnection()
    cache = {"town:nowhere": None}
    with patch.object(gp, "geocode", AsyncMock()) as geo:
        assert await gp.get_cached_or_geocode(conn, None, "town:nowhere", {}, cache) is None
    geo.assert_not_called()


async def test_successful_lookup_is_stored():
    conn = MockConnection()
    cache: dict = {}
    with patch.object(gp, "geocode", AsyncMock(return_value=(1.0, 2.0, "Indore"))):
        result = await gp.get_cached_or_geocode(conn, None, "pin:452001", {}, cache)

    assert result == (1.0, 2.0, "Indore")
    assert cache["pin:452001"] == result
    assert conn.execute.call_args.args[1:] == ("pin:452001", 1.0, 2.0, "Indore")


async def test_failed_lookup_caches_miss():
    conn = MockConnection()
    cache: dict = {}
    with patch.object(gp, "geocode", AsyncMock(return_value=None)):
        assert await gp.get_cached_or_geocode(conn, None, "town:nowhere", {}, cache) is None

    assert cache == {"town:nowhere": None}
    sql, key = conn.execute.call_args.args
    assert "INSERT INTO public.geo_cache (query_key, source)" in sql
    assert key == "town:nowhere"
