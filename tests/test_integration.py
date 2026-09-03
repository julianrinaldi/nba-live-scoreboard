"""Offline regression tests for installation and the card-facing contract."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.nba_live_scoreboard import (
    CARD_FILENAME,
    HACS_URL_BASE,
    LEGACY_URL_BASE,
    _async_register_card,
    _sync_card_to_www_community,
)
from custom_components.nba_live_scoreboard.sensor import build_state_attributes


def test_bundled_card_is_copied_to_hacs_community_directory(tmp_path):
    source = tmp_path / CARD_FILENAME
    source.write_text("export const version = 'one';")
    result = _sync_card_to_www_community(str(tmp_path / "config"), source)
    assert result == tmp_path / "config/www/community/nba_live_scoreboard" / CARD_FILENAME
    assert result.read_bytes() == source.read_bytes()


def test_same_size_same_mtime_card_update_is_not_skipped(tmp_path):
    source = tmp_path / CARD_FILENAME
    source.write_text("first")
    result = _sync_card_to_www_community(str(tmp_path / "config"), source)
    source.write_text("newer")
    old_stat = result.stat()
    os.utime(source, (old_stat.st_atime, old_stat.st_mtime))
    assert source.stat().st_size == result.stat().st_size
    _sync_card_to_www_community(str(tmp_path / "config"), source)
    assert result.read_text() == "newer"


def test_failed_community_copy_returns_fallback(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("read-only configuration directory")

    monkeypatch.setattr(Path, "mkdir", fail)
    assert _sync_card_to_www_community(str(tmp_path), tmp_path / CARD_FILENAME) is None


def _resource_hass(monkeypatch, items):
    const = ModuleType("homeassistant.components.lovelace.const")
    const.DOMAIN = "lovelace"
    monkeypatch.setitem(sys.modules, const.__name__, const)
    resources = SimpleNamespace(
        loaded=False,
        async_load=AsyncMock(),
        async_items=lambda: items,
        async_create_item=AsyncMock(),
        async_update_item=AsyncMock(),
    )
    return SimpleNamespace(data={"lovelace": SimpleNamespace(resources=resources)}), resources


@pytest.mark.asyncio
async def test_resource_is_automatically_registered(monkeypatch):
    hass, resources = _resource_hass(monkeypatch, [])
    url = f"{HACS_URL_BASE}?v=100"
    await _async_register_card(hass, url, HACS_URL_BASE)
    resources.async_load.assert_awaited_once()
    resources.async_create_item.assert_awaited_once_with({"url": url, "res_type": "module"})


@pytest.mark.asyncio
async def test_legacy_resource_migrates_and_cache_buster_updates(monkeypatch):
    hass, resources = _resource_hass(
        monkeypatch,
        [{"id": "our-card", "url": f"{LEGACY_URL_BASE}?v=099", "res_type": "module"}],
    )
    url = f"{HACS_URL_BASE}?v=100"
    await _async_register_card(hass, url, HACS_URL_BASE)
    resources.async_update_item.assert_awaited_once_with(
        "our-card", {"url": url, "res_type": "module"}
    )
    resources.async_create_item.assert_not_awaited()


@pytest.mark.asyncio
async def test_unrelated_resource_containing_our_name_is_untouched(monkeypatch):
    hass, resources = _resource_hass(
        monkeypatch,
        [{"id": "other", "url": f"/other-card.js?example={HACS_URL_BASE}"}],
    )
    await _async_register_card(hass, f"{HACS_URL_BASE}?v=100", HACS_URL_BASE)
    resources.async_update_item.assert_not_awaited()
    resources.async_create_item.assert_awaited_once()


@pytest.mark.asyncio
async def test_nba_registration_leaves_other_sports_resources_untouched(monkeypatch):
    originals = [
        {"id": "nfl", "url": "/hacsfiles/nfl_live_scoreboard/nfl-live-game-card.js?v=100", "type": "module"},
        {"id": "mlb", "url": "/hacsfiles/mlb_live_scoreboard/mlb-live-game-card.js?v=1282", "type": "module"},
        {"id": "nhl", "url": "/hacsfiles/nhl_live_scoreboard/nhl-live-game-card.js?v=100", "type": "module"},
    ]
    hass, resources = _resource_hass(monkeypatch, originals)
    url = f"{HACS_URL_BASE}?v=100"
    await _async_register_card(hass, url, HACS_URL_BASE)
    resources.async_update_item.assert_not_awaited()
    resources.async_create_item.assert_awaited_once_with({"url": url, "res_type": "module"})


@pytest.mark.asyncio
async def test_current_resource_is_not_duplicated(monkeypatch):
    url = f"{HACS_URL_BASE}?v=100"
    hass, resources = _resource_hass(
        monkeypatch, [{"id": "our-card", "url": url, "type": "module"}]
    )
    await _async_register_card(hass, url, HACS_URL_BASE)
    resources.async_update_item.assert_not_awaited()
    resources.async_create_item.assert_not_awaited()


@pytest.mark.asyncio
async def test_resource_type_is_repaired_even_at_current_url(monkeypatch):
    url = f"{HACS_URL_BASE}?v=100"
    hass, resources = _resource_hass(
        monkeypatch, [{"id": "our-card", "url": url, "type": "js"}]
    )
    await _async_register_card(hass, url, HACS_URL_BASE)
    resources.async_update_item.assert_awaited_once_with(
        "our-card", {"url": url, "res_type": "module"}
    )


def test_sensor_contract_contains_nba_fields_and_no_other_sport_fields():
    play = {
        "id": "1234",
        "text": "Jalen Brunson makes three point jumper",
        "period": 3,
        "clock": "2:00",
        "away_score": 1,
        "home_score": 2,
        "scoring_play": True,
        "score_value": 3,
        "coordinate": {},
        "is_shot": True,
        "points_attempted": 3,
        "team_id": "18",
        "unused_raw_payload": {"large": True},
    }
    data = SimpleNamespace(
        team_abbr="NY", team_id=18, team_name="New York Knicks",
        mode="live", is_live=True, is_delayed=False, status_text="2:00 - 3rd",
        display_event_id="123", live_event_id="123", previous_event_id="122", next_event_id="124",
        selected_competition={"id": "123"}, period_context={"period": 3, "display_clock": "2:00"},
        recent_plays=[play], scoring_plays=[play], away_team={}, home_team={},
        featured_players={"away": {}, "home": {}}, situation={"away_timeouts": 2, "home_timeouts": 2},
        current_period={"id": "3", "number": 3}, team_stats={}, win_probability={}, leaders={},
        division_standings={}, highlights_url="",
    )
    attrs = build_state_attributes(data)
    assert attrs["league"] == "NBA"
    assert attrs["game_active"] is True
    assert attrs["period_context"]["period"] == 3
    assert attrs["recent_plays"][0]["score_value"] == 3
    assert attrs["recent_plays"][0]["coordinate"] == {}
    assert "unused_raw_payload" not in attrs["recent_plays"][0]
    assert not {
        "inning_context", "current_batter", "current_pitcher", "current_pitches",
        "batter_stats", "pitcher_stats", "on_deck", "due_up", "lineups", "decisions",
        "quarterbacks", "current_drive", "down", "distance", "yard_line", "goalies", "is_shootout",
    }.intersection(attrs)


@pytest.mark.asyncio
async def test_options_actions_are_validated_and_transient_scripts_unloaded(monkeypatch):
    from homeassistant.helpers import config_validation
    from homeassistant.helpers import script as script_helper

    from custom_components.nba_live_scoreboard import coordinator as module

    raw = [{"event": "test", "event_data": {"points": "{{ score_delta }}"}}]
    schema_result = [{"validated_template": True}]
    fully_validated = [{"validated_action": True}]
    schema = Mock(return_value=schema_result)
    validation = AsyncMock(return_value=fully_validated)
    monkeypatch.setattr(config_validation, "SCRIPT_SCHEMA", schema, raising=False)
    monkeypatch.setattr(script_helper, "async_validate_actions_config", validation, raising=False)
    instance = SimpleNamespace(async_run=AsyncMock(), async_unload=AsyncMock())
    constructor = Mock(return_value=instance)
    monkeypatch.setattr(module, "Script", constructor)
    coordinator = object.__new__(module.NbaLiveScoreboardCoordinator)
    coordinator.hass = SimpleNamespace()
    payload = {"score_delta": 1}
    await coordinator._run_event_action("nba_live_scoreboard_team_scored", raw, payload)
    schema.assert_called_once_with(raw)
    validation.assert_awaited_once_with(coordinator.hass, schema_result)
    assert constructor.call_args.args[1] is fully_validated
    assert instance.async_run.call_args.args[0] == payload
    instance.async_unload.assert_awaited_once()
