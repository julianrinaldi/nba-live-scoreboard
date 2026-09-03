"""Offline NBA regressions using captured ESPN data and explicit edge cases."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.nba_live_scoreboard.const import (
    EVENT_GAME_ENDED,
    EVENT_GAME_LOST,
    EVENT_GAME_STARTED,
    EVENT_GAME_WON,
    EVENT_OPPONENT_SCORED,
    EVENT_TEAM_SCORED,
    NBA_TEAM_MAP,
    SCHEDULE_STALE_FALLBACK_SECONDS,
    SCHEDULE_TTL_SECONDS,
    USER_AGENT,
)
from custom_components.nba_live_scoreboard.coordinator import (
    NbaLiveScoreboardCoordinator as C,
)
from custom_components.nba_live_scoreboard.coordinator import (
    NbaLiveScoreboardData as Data,
)
from custom_components.nba_live_scoreboard.coordinator import (
    _is_final,
    _optional_int,
    _parse_iso_ts,
    _safe_int,
    _team_id,
)

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def final():
    return fixture("summary_401809234_regulation.json")


@pytest.fixture
def overtime():
    return fixture("summary_401810626_overtime.json")


@pytest.fixture
def double_overtime():
    return fixture("summary_401810581_double_overtime.json")


@pytest.fixture
def coordinator():
    hass = SimpleNamespace(config=SimpleNamespace(time_zone="America/New_York"))
    entry = SimpleNamespace(data={"team": "NY"}, title="NBA", options={})
    return C(hass, entry)


def competition(state="in", name="STATUS_IN_PROGRESS", away=1, home=2, period=2):
    return {
        "id": "1", "date": "2026-04-11T21:00Z", "season": 2026, "seasonType": 2,
        "status": {"period": period, "displayClock": "8:15", "type": {
            "state": state, "name": name, "completed": state == "post" and name == "STATUS_FINAL",
            "detail": "Final" if state == "post" else "8:15 - 2nd Quarter"}},
        "competitors": [
            {"homeAway": "home", "score": str(home), "team": {"id": "18", "abbreviation": "NY", "displayName": "New York Knicks"}},
            {"homeAway": "away", "score": str(away), "team": {"id": "5", "abbreviation": "CLE", "displayName": "Cleveland Cavaliers"}},
        ],
    }


def data(comp=None, event_id="1", is_live=True, delayed=False):
    comp = comp or competition()
    result = Data(team_abbr="NY", team_id=18, team_name="New York Knicks", display_event_id=event_id,
                  selected_competition=comp, period_context={"period": comp["status"]["period"], "display_clock": "8:15"},
                  is_live=is_live, is_delayed=delayed, status_text="8:15 - 2nd Quarter")
    return result


def event(event_id, hours, state="pre", name="STATUS_SCHEDULED", phase=2):
    timestamp = datetime(2026, 4, 11, 21, tzinfo=UTC) + timedelta(hours=hours)
    comp = competition(state, name)
    comp["id"] = str(event_id)
    return {"id": str(event_id), "date": timestamp.isoformat(), "season": {"year": 2026},
            "seasonType": {"type": phase}, "competitions": [comp]}


@pytest.mark.parametrize(("value", "expected"), [(None, 0), ("", 0), ("2", 2), ("2.0", 2), ("bad", 0),
                                                 ("nan", 0), ("inf", 0), (True, 0), ({"value": 3}, 3)])
def test_safe_scores(value, expected):
    assert _safe_int(value) == expected


def test_dates_and_reference_ids():
    assert _parse_iso_ts("2026-04-11T21:00Z") == datetime(2026, 4, 11, 21, tzinfo=UTC).timestamp()
    assert _parse_iso_ts("2026-04-11T21:00:00") is None
    assert _parse_iso_ts("bad") is None
    assert _team_id({"$ref": "http://sports.core.api.espn.com/x/competitors/13?lang=en"}) == "13"
    assert _team_id("13") == "13"
    assert _optional_int("0") == 0



def test_exact_current_30_team_map_and_contact_user_agent():
    teams = fixture("teams_20260903.json")["teams"]
    assert {t["abbreviation"]: int(t["id"]) for t in teams} == NBA_TEAM_MAP
    assert len(NBA_TEAM_MAP) == 30
    assert (NBA_TEAM_MAP["NY"], NBA_TEAM_MAP["GS"], NBA_TEAM_MAP["UTAH"]) == (18, 9, 26)
    assert "(+https://github.com/julianrinaldi/nba-live-scoreboard)" in USER_AGENT


@pytest.mark.parametrize(("period", "label"), [(1, "Q1"), (2, "Q2"), (3, "Q3"), (4, "Q4"), (5, "OT"), (6, "2OT"), (7, "3OT")])
def test_four_quarters_and_unlimited_overtime(period, label):
    assert C._period_label(period) == label


@pytest.mark.parametrize(("filename", "period", "label", "scores"), [
    ("summary_401809234_regulation.json", 4, "Final", ("111", "119")),
    ("summary_401810626_overtime.json", 5, "Final/OT", ("137", "134")),
    ("summary_401810581_double_overtime.json", 6, "Final/2OT", ("127", "134")),
])
def test_real_finals_preserve_quarters_and_overtime(filename, period, label, scores):
    summary = fixture(filename)
    comp = summary["header"]["competitions"][0]
    ctx = C._normalize_period_context(summary, comp)
    assert (ctx["period"], ctx["label"], ctx["display_clock"]) == (period, label, "")
    assert "is_shootout" not in ctx
    compact = C._compact_competition(comp)
    sides = {c["homeAway"]: c for c in compact["competitors"]}
    assert (sides["away"]["score"], sides["home"]["score"]) == scores
    assert all(len(c["linescores"]) == period for c in compact["competitors"])


@pytest.mark.parametrize(("period", "clock"), [(1, "12:00"), (4, "0.4"), (5, "5:00"), (6, "4:59")])
def test_live_clock_is_authoritative_countdown(final, period, clock):
    comp = competition(period=period)
    comp["status"]["displayClock"] = clock
    final["plays"] = [p for p in final["plays"] if p["period"]["number"] <= period]
    assert C._normalize_period_context(final, comp)["display_clock"] == clock


def test_halftime_and_quarter_breaks_clear_clock():
    comp = competition(name="STATUS_HALFTIME", period=2)
    comp["status"]["type"]["detail"] = "Halftime"
    ctx = C._normalize_period_context({}, comp)
    assert ctx["is_halftime"] and ctx["is_intermission"]
    assert ctx["label"] == "Halftime" and ctx["display_clock"] == ""
    comp = competition(name="STATUS_END_PERIOD", period=1)
    comp["status"]["type"]["detail"] = "End of 1st Quarter"
    ctx = C._normalize_period_context({}, comp)
    assert ctx["is_end_period"] and not ctx["is_halftime"]


def test_missing_live_clock_never_reuses_an_old_play(final):
    comp = competition(period=4)
    comp["status"].pop("displayClock")
    comp["status"]["type"]["detail"] = "In Progress"
    assert C._normalize_period_context(final, comp)["display_clock"] == ""


def test_real_plays_sort_deduplicate_and_use_countdown(final):
    final["plays"] = [*reversed(final["plays"]), final["plays"][0]]
    periods = C._all_periods(final)
    assert [p["number"] for p in periods] == [1, 2, 3, 4]
    plays = C._normalize_recent_plays(final, periods[0])
    assert len(plays) == len({p["id"] for p in plays})
    assert [p["clock"] for p in plays[:3]] == ["12:00", "11:45", "11:20"]
    assert [p["score_value"] for p in plays[:3]] == [0, 2, 3]
    assert {p["score_value"] for p in plays if p["scoring_play"]} == {1, 2, 3}


def test_new_empty_period_does_not_repeat_earlier_plays(final):
    final["header"]["competitions"][0]["status"] = competition(period=5)["status"]
    period = C._selected_period(final)
    assert period["number"] == 5
    assert C._normalize_recent_plays(final, period) == []


def test_all_real_scoring_plays_match_quarter_linescores(final):
    comp = final["header"]["competitions"][0]
    sides = {c["homeAway"]: c for c in comp["competitors"]}
    for period in C._all_periods(final):
        normalized = C._normalize_period(period, comp)
        i = period["number"] - 1
        assert normalized["away_points"] == int(sides["away"]["linescores"][i]["displayValue"])
        assert normalized["home_points"] == int(sides["home"]["linescores"][i]["displayValue"])
        assert normalized["points"] == normalized["away_points"] + normalized["home_points"]


def test_scoring_summary_keeps_one_two_three_points_and_double_overtime(final, double_overtime):
    scores = C._normalize_scoring_plays(final)
    assert {s["score_value"] for s in scores} == {1, 2, 3}
    assert all("is_shootout" not in s for s in scores)
    last = C._normalize_scoring_plays(double_overtime)[-1]
    assert (last["period_number"], last["away_score"], last["home_score"]) == (6, 127, 134)


def test_real_fouls_shots_and_invalid_coordinate_sentinels(final):
    plays = C._normalize_recent_plays(final, C._all_periods(final)[0])
    assert any(p["is_foul"] for p in plays)
    assert any(p["is_shot"] and p["points_attempted"] == 3 for p in plays)
    free_throw = next(p for p in plays if p["play_type"] == "Free Throw - 1 of 3")
    assert free_throw["score_value"] == 1 and free_throw["is_shot"]
    assert free_throw["coordinate"] == {}
    assert free_throw["is_free_throw"] is True
    assert plays[1]["coordinate"] == {"x": 26, "y": 12}
    assert plays[2]["coordinate"] == {"x": 48, "y": 0}
    assert not plays[0]["is_shot"]


@pytest.mark.parametrize("coordinate", [{"x": -1, "y": 0}, {"x": 51, "y": 0}, {"x": 0, "y": -5},
    {"x": 0, "y": 91}, {"x": True, "y": 0}, {"x": "25", "y": 10}, {"x": float("nan"), "y": 0},
    {"x": 0, "y": float("inf")}, {"x": -214748340, "y": -214748365}, {}])
def test_bad_court_coordinates_are_omitted(coordinate):
    play = {"id": "1", "text": "Shot", "type": {"text": "Jump Shot"}, "period": {"number": 1},
            "shootingPlay": True, "pointsAttempted": 2, "coordinate": coordinate, "team": {"id": "18"}}
    summary = {"header": {"competitions": [competition(period=1)]}, "plays": [play]}
    assert C._normalize_recent_plays(summary)[0]["coordinate"] == {}


@pytest.mark.parametrize("override", [{"pointsAttempted": 1}, {"type": {"text": "Free Throw - 1 of 2"}},
    {"shootingPlay": False}, {"team": {"id": "999"}}, {"team": {}}])
def test_only_known_team_field_goals_get_coordinates(override):
    play = {"id": "1", "text": "Shot", "type": {"text": "Jump Shot"}, "period": {"number": 1},
            "shootingPlay": True, "pointsAttempted": 2, "coordinate": {"x": 25, "y": 10}, "team": {"id": "18"}}
    play.update(override)
    summary = {"header": {"competitions": [competition(period=1)]}, "plays": [play]}
    assert C._normalize_recent_plays(summary)[0]["coordinate"] == {}


def test_optional_possession_timeouts_and_shot_clock():
    comp = competition()
    assert C._normalize_situation({}, comp) == {
        "possession_team_id": "", "away_timeouts": None, "home_timeouts": None, "shot_clock": None}
    source = {"possession": {"id": "18"}, "awayTimeouts": {"timeoutsRemainingCurrent": 0},
              "homeTimeouts": {"timeoutsRemainingCurrent": 3}, "shotClock": 14.2}
    assert C._normalize_situation({}, comp, source) == {
        "possession_team_id": "18", "away_timeouts": 0, "home_timeouts": 3, "shot_clock": 14.2}
    comp["competitors"][0]["possession"] = True
    assert C._normalize_situation({}, comp)["possession_team_id"] == "18"
    comp["competitors"][1]["possession"] = True
    assert C._normalize_situation({}, comp)["possession_team_id"] == ""
    assert C._normalize_situation({}, competition("post", "STATUS_FINAL"), source)["shot_clock"] is None


@pytest.mark.parametrize("value", [True, -1, 25, "NaN", "inf", "bad"])
def test_invalid_shot_clock_stays_unknown(value):
    assert C._normalize_situation({}, competition(), {"shotClock": value})["shot_clock"] is None


def test_real_boxscore_shooting_and_dnp_flags(final):
    teams = C._normalize_team_stats(final)
    category = teams["home"]["categories"][0]
    assert category["name"] == "players"
    assert category["columns"][:5] == ["MIN", "PTS", "FG", "3PT", "FT"]
    brunson = next(r for r in category["rows"] if r["id"] == "3934672")
    values = C._stats_by_key(category, brunson)
    assert values["points"] == "23"
    assert values["fieldGoalsMade-fieldGoalsAttempted"] == "5-18"
    assert brunson["starter"] and not brunson["did_not_play"]
    assert any(r["did_not_play"] for r in category["rows"])


def test_featured_players_are_game_scoring_leaders(final):
    featured = C._normalize_featured_players(final, C._normalize_team_stats(final))
    assert featured["away"]["display_name"] == "Donovan Mitchell"
    assert featured["away"]["game_stats"]["points"] == "31"
    assert featured["home"]["display_name"] == "OG Anunoby"
    assert featured["home"]["game_stats"]["points"] == "24"
    assert C._normalize_featured_players({}, {"away": {}, "home": {}}, live=False) == {"away": {}, "home": {}}


def test_real_leaders_use_game_team_not_current_athlete_team(final):
    leaders = C._normalize_leaders(final)
    assert any(p["id"] == "4066421" and p["category"] == "Assists" for p in leaders["away"])
    assert any(p["id"] == "3934719" for p in leaders["home"])


def test_season_averages_and_career_totals_remain_distinct():
    raw = fixture("athlete_3934672_stats.json")
    line = C._extract_season_line(raw)
    assert str(line["season"]) in {"2026", "2025-26", "25-26"}
    category = line["categories"]["players"]
    values = dict(zip(category["keys"], category["stats"], strict=True))
    assert values["avgPoints"] == "26.0"
    assert values["avgRebounds"] == "3.3"
    assert values["avgAssists"] == "6.8"
    assert "1927" not in category["stats"]
    card = C._parse_player_card("3934672", fixture("athlete_3934672_bio.json"), raw)
    assert card["bio"]["name"] == "Jalen Brunson" and card["bio"]["position"] == "G"
    assert len(card["career"]["seasons"]) == 2
    assert card["career"]["seasons"][-1]["team"] == "NY"


def test_actual_atlantic_standings_have_division_relative_games_behind():
    standings = fixture("standings_atlantic_2026.json")
    index = C._team_id_division_index(fixture("groups_20260903.json"))
    result = C._normalize_standings(standings, index, 18)
    assert result["division_name"] == "Atlantic"
    entries = {e["team_id"]: e for e in result["entries"]}
    assert (entries["18"]["wins"], entries["18"]["losses"]) == ("53", "29")
    assert entries["18"]["win_percent"] == ".646"
    assert float(entries["18"]["games_behind"]) == 3
    assert C._records_from_standings(standings)["18"].startswith("53-29")


@pytest.mark.asyncio
@pytest.mark.parametrize("metadata_mode", ["observed", "missing_requested", "stale_requested"])
async def test_current_schedule_uses_effective_year(coordinator, monkeypatch, metadata_mode):
    monkeypatch.setattr("custom_components.nba_live_scoreboard.coordinator.time.time",
                        lambda: datetime(2026, 9, 3, tzinfo=UTC).timestamp())
    default = fixture("schedule_ny_default_20260903.json")
    default["season"]["year"] = 2026  # Explicit stale generic-metadata case.
    if metadata_mode == "missing_requested":
        default.pop("requestedSeason")
    elif metadata_mode == "stale_requested":
        default["requestedSeason"]["year"] = 2025
    async def fetch(url):
        return copy.deepcopy(default) if "?" not in url else {"events": []}
    coordinator._get_json = AsyncMock(side_effect=fetch)
    schedule = await coordinator._fetch_schedule()
    assert schedule["season"]["year"] == 2027
    assert coordinator._select_event(schedule["events"])[:4] == ("", "401914101", "", "401914101")
    requested = [c.args[0] for c in coordinator._get_json.await_args_list if "?" in c.args[0]]
    assert requested and all("season=2027" in url for url in requested)


def test_schedule_selection_sorts_and_prefers_live(coordinator, monkeypatch):
    now = datetime(2026, 4, 11, 21, tzinfo=UTC).timestamp()
    monkeypatch.setattr("custom_components.nba_live_scoreboard.coordinator.time.time", lambda: now)
    previous, future, live = event(1, -48, "post", "STATUS_FINAL"), event(3, 48), event(2, -1, "in", "STATUS_IN_PROGRESS")
    result = coordinator._select_event([future, live, previous])
    assert result[:4] == ("1", "3", "2", "2")


def test_recent_final_holds_then_next_game_and_stale_pregame_is_fetched(coordinator, monkeypatch):
    now = datetime(2026, 4, 11, 21, tzinfo=UTC).timestamp()
    monkeypatch.setattr("custom_components.nba_live_scoreboard.coordinator.time.time", lambda: now)
    assert coordinator._select_event([event(1, -10, "post", "STATUS_FINAL"), event(2, 36)])[3] == "1"
    assert coordinator._select_event([event(1, -20, "post", "STATUS_FINAL"), event(2, 36)])[3] == "2"
    assert coordinator._select_event([event(2, -1), event(3, 48)])[3] == "2"


def test_merge_deduplicates_phases_and_rejects_wrong_year():
    early, later = event(1, -24, phase=1), event(2, 24, phase=2)
    wrong = copy.deepcopy(later)
    wrong["id"], wrong["season"]["year"] = "3", 2025
    merged = C._merge_schedules([{"events": [later]}, {"events": [wrong, early, later]}], 2026)
    assert [e["id"] for e in merged["events"]] == ["1", "2"]


@pytest.mark.parametrize(("offset", "expected"), [(-99, ("1", -1, False, True)), (0, ("2", 0, True, True)), (99, ("3", 1, True, False))])
def test_game_navigation_clamps(offset, expected):
    assert C._event_at_offset([event(3, 24), event(1, -24), event(2, 0)], "2", offset) == expected


@pytest.mark.parametrize("delta", [1, 2, 3])
def test_one_two_three_point_events_use_nba_context(delta):
    events = C._detect_game_events(data(competition(home=2)), data(competition(home=2 + delta)), 18)
    assert events[0][0] == EVENT_TEAM_SCORED
    assert events[0][1]["score_delta"] == delta
    assert events[0][1]["period"] == 2
    assert events[0][1]["team_abbr"] == "NY"
    assert "is_shootout" not in events[0][1]
    assert "down" not in events[0][1]
    assert C._detect_game_events(data(), data(competition(away=2)), 18)[0][0] == EVENT_OPPONENT_SCORED


def test_score_event_does_not_attach_an_old_or_opponent_scoring_description():
    previous, current = data(competition(home=2)), data(competition(home=3))
    current.scoring_plays = [{"team_id": "18", "home_score": 2, "away_score": 1, "text": "An earlier Knicks score"}]
    current.recent_plays = [{"team_id": "5", "home_score": 2, "away_score": 1, "scoring_play": True, "text": "An opponent score"}]
    events = C._detect_game_events(previous, current, 18)
    assert events[0][1]["scoring_play_text"] == ""
    current.scoring_plays.append({"team_id": "18", "home_score": 3, "away_score": 1, "text": "The actual new Knicks score"})
    assert C._detect_game_events(previous, current, 18)[0][1]["scoring_play_text"] == "The actual new Knicks score"


@pytest.mark.parametrize("delta", [-2, -1, 0, 4, 6, 10])
def test_score_corrections_and_multiple_missed_scores_not_announced(delta):
    assert C._detect_game_events(data(competition(home=3)), data(competition(home=3 + delta)), 18) == []


def test_startup_new_game_and_delay_suppress_score_events():
    current = data()
    assert C._detect_game_events(None, current, 18) == []
    assert C._detect_game_events(data(event_id="0"), current, 18) == []
    assert C._detect_game_events(data(), data(competition(home=3), delayed=True), 18) == []
    assert C._detect_game_events(data(), current, 129764) == []


def test_delay_before_tipoff_then_live_starts_once():
    scheduled = data(competition("pre", "STATUS_SCHEDULED", away=0, home=0, period=0), is_live=False)
    delayed = data(competition("pre", "STATUS_DELAYED", away=0, home=0, period=0), delayed=True)
    current = data(competition(away=0, home=0, period=1))
    assert C._detect_game_events(scheduled, delayed, 18) == []
    assert [e[0] for e in C._detect_game_events(delayed, current, 18)] == [EVENT_GAME_STARTED]
    assert C._detect_game_events(current, current, 18) == []


@pytest.mark.parametrize(("home", "away", "expected"), [(3, 2, [EVENT_GAME_ENDED, EVENT_GAME_WON]), (2, 3, [EVENT_GAME_ENDED, EVENT_GAME_LOST])])
def test_final_won_lost(home, away, expected):
    previous = data(competition(home=home, away=away))
    current = data(competition("post", "STATUS_FINAL", home=home, away=away), is_live=False)
    assert [e[0] for e in C._detect_game_events(previous, current, 18)] == expected


@pytest.mark.parametrize("missing", [None, "", "bad", "nan", "-1"])
def test_final_waits_for_numeric_scores(missing):
    previous = data(competition(home=3, away=2))
    incomplete = data(competition("post", "STATUS_FINAL", home=3, away=2), is_live=False)
    incomplete.selected_competition["competitors"][0]["score"] = missing
    current = data(competition("post", "STATUS_FINAL", home=3, away=2), is_live=False)
    assert C._detect_game_events(previous, incomplete, 18) == []
    assert [e[0] for e in C._detect_game_events(incomplete, current, 18)] == [EVENT_GAME_ENDED, EVENT_GAME_WON]


@pytest.mark.parametrize("name", ["STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_CANCELLED"])
def test_unplayed_post_status_is_not_a_final(name):
    comp = competition("post", name)
    comp["status"]["type"]["completed"] = False
    assert not _is_final(comp)
    assert C._detect_game_events(data(), data(comp, is_live=False), 18) == []


@pytest.mark.parametrize("name", ["STATUS_DELAYED", "STATUS_SUSPENDED"])
def test_interruptions_keep_fast_poll(name):
    assert C._resolve_status_info(competition(name=name))[1:] == (True, True)


def test_score_rebound_and_missed_polling_are_rebaselined(coordinator, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("custom_components.nba_live_scoreboard.coordinator.time.time", lambda: now[0])
    high, low = data(competition(home=3)), data(competition(home=2))
    coordinator._filter_score_rebounds([], high)
    now[0] += 5
    coordinator._filter_score_rebounds([], low)
    now[0] += 5
    assert coordinator._filter_score_rebounds(C._detect_game_events(low, high, 18), high) == []
    current = data(competition(home=4))
    now[0] += 5
    assert coordinator._filter_score_rebounds(C._detect_game_events(high, current, 18), current)
    missed = data(competition(home=5))
    now[0] += 180
    assert coordinator._filter_score_rebounds(C._detect_game_events(current, missed, 18), missed) == []


def test_start_and_final_deduplication_is_per_game(coordinator):
    event_pair = (EVENT_GAME_STARTED, {})
    assert coordinator._suppress_repeat_once_events([event_pair], "1") == [event_pair]
    assert coordinator._suppress_repeat_once_events([event_pair], "1") == []
    assert coordinator._suppress_repeat_once_events([event_pair], "2") == [event_pair]


@pytest.mark.asyncio
async def test_optional_cache_stale_deadline_is_bounded(coordinator, monkeypatch):
    monkeypatch.setattr("custom_components.nba_live_scoreboard.coordinator.time.time", lambda: 110)
    coordinator._json_cache["x"] = (0, {"retained": True})
    coordinator._get_json = AsyncMock(side_effect=RuntimeError("offline"))
    assert await coordinator._cached_json("x", "https://example.com", 100, 20) == {"retained": True}
    assert await coordinator._cached_json("x", "https://example.com", 100, 5) == {}


@pytest.mark.asyncio
async def test_partial_schedule_failure_cannot_extend_original_cache_age(coordinator, monkeypatch):
    now = [SCHEDULE_TTL_SECONDS + 1]
    monkeypatch.setattr("custom_components.nba_live_scoreboard.coordinator.time.time", lambda: now[0])
    pre, regular, post = event(1, -24, phase=1), event(2, 0, phase=2), event(3, 24, phase=3)
    coordinator._schedule_cache = (0, {"season": {"year": 2026}, "events": [pre, regular, post]})
    async def fetch(url):
        if "seasontype=2" in url:
            raise RuntimeError("Regular season unavailable")
        if "seasontype=3" in url:
            return {"events": [post]}
        return {"season": {"year": 2026, "type": 1}, "events": [pre]}
    coordinator._get_json = AsyncMock(side_effect=fetch)
    assert len((await coordinator._fetch_schedule())["events"]) == 3
    assert coordinator._schedule_cache[0] == 0
    now[0] = SCHEDULE_TTL_SECONDS + SCHEDULE_STALE_FALLBACK_SECONDS + 1
    with pytest.raises(Exception, match="Unable to fetch NBA schedule"):
        await coordinator._fetch_schedule()


@pytest.mark.asyncio
async def test_player_ids_are_validated_and_requests_cached(coordinator):
    with pytest.raises(ValueError):
        await coordinator.async_get_player_card("../13")
    with pytest.raises(ValueError):
        await coordinator.async_get_team_season_stats(["1", "not-an-id"])
    coordinator._get_json = AsyncMock(side_effect=[fixture("athlete_3934672_bio.json"), fixture("athlete_3934672_stats.json")])
    card = await coordinator.async_get_player_card("3934672")
    assert card["bio"]["name"] == "Jalen Brunson"
    assert await coordinator.async_get_player_card("3934672") == card
    assert coordinator._get_json.await_count == 2


@pytest.mark.asyncio
async def test_season_batch_deduplicates_and_isolates_failures(coordinator):
    coordinator._get_one_season_line = AsyncMock(side_effect=[{"season": "2026"}, RuntimeError("offline")])
    assert await coordinator.async_get_team_season_stats(["1", "1", "2"]) == {"1": {"season": "2026"}}
    assert coordinator._get_one_season_line.await_count == 2


def test_poll_intervals(coordinator, monkeypatch):
    now = datetime(2026, 4, 11, 21, tzinfo=UTC).timestamp()
    monkeypatch.setattr("custom_components.nba_live_scoreboard.coordinator.time.time", lambda: now)
    assert coordinator._compute_update_interval(data(), []).total_seconds() == 5
    assert coordinator._compute_update_interval(data(is_live=False), [event(1, 0.1)]).total_seconds() == 30
    assert coordinator._compute_update_interval(data(is_live=False), [event(1, 24 * 7)]).total_seconds() == 300


@pytest.mark.asyncio
async def test_play_in_is_fetched_separately_from_postseason(coordinator):
    default = fixture("schedule_phi_postseason_2026.json")
    play_in = fixture("schedule_phi_playin_2026.json")
    async def fetch(url):
        if "?" not in url:
            return copy.deepcopy(default)
        if "seasontype=5" in url:
            return copy.deepcopy(play_in)
        return {"events": []}
    coordinator.team_abbr = "PHI"
    coordinator._get_json = AsyncMock(side_effect=fetch)
    schedule = await coordinator._fetch_schedule()
    assert schedule["season"]["year"] == 2026
    assert any(e["id"] == "401866757" and e["seasonType"]["type"] == 5 for e in schedule["events"])
    assert any("season=2026&seasontype=5" in call.args[0] for call in coordinator._get_json.await_args_list)


def test_traded_player_uses_total_average_row_without_adding_rates():
    raw = fixture("athlete_3934672_stats.json")
    category = next(c for c in raw["categories"] if c["name"] == "averages")
    total = copy.deepcopy(category["statistics"][-1])
    total["teamId"] = "0"
    total["teamSlug"] = "total"
    split = copy.deepcopy(total)
    split["teamId"], split["teamSlug"] = "5", "cleveland-cavaliers"
    split["stats"][category["names"].index("avgPoints")] = "30.0"
    category["statistics"] = [total, split]
    # This is a synthetic trade mutation of actual average fields. The
    # season-wide row wins even when a team split happens to be last.
    result = C._extract_season_line(raw)["categories"]["players"]
    assert result["stats"][result["keys"].index("avgPoints")] == "26.0"


def test_upward_review_of_same_basket_is_not_a_new_score():
    previous, current = data(competition(home=102, away=100)), data(competition(home=103, away=100))
    previous.scoring_plays = [{"id": "reviewed", "team_id": "18", "home_score": 102, "away_score": 100,
                               "score_value": 2, "text": "Two point shot"}]
    current.scoring_plays = [{"id": "reviewed", "team_id": "18", "home_score": 103, "away_score": 100,
                              "score_value": 3, "text": "Reviewed three point shot"}]
    assert C._detect_game_events(previous, current, 18) == []


def test_play_arriving_before_score_does_not_hide_the_new_basket():
    previous, current = data(competition(home=100, away=100)), data(competition(home=103, away=100))
    play = {"id": "ahead", "team_id": "18", "home_score": 103, "away_score": 100,
            "score_value": 3, "text": "New three point basket"}
    previous.scoring_plays = [copy.deepcopy(play)]
    current.scoring_plays = [copy.deepcopy(play)]
    events = C._detect_game_events(previous, current, 18)
    assert len(events) == 1 and events[0][0] == EVENT_TEAM_SCORED
    assert events[0][1]["score_delta"] == 3
    assert events[0][1]["scoring_play_text"] == "New three point basket"


def test_score_ahead_of_play_feed_fires_without_unrelated_description():
    previous, current = data(competition(home=100, away=100)), data(competition(home=103, away=100))
    current.scoring_plays = [{"id": "old", "team_id": "18", "home_score": 100, "away_score": 100,
                              "score_value": 2, "text": "An older basket"}]
    events = C._detect_game_events(previous, current, 18)
    assert len(events) == 1 and events[0][1]["score_delta"] == 3
    assert events[0][1]["scoring_play_text"] == ""


@pytest.mark.asyncio
async def test_real_final_assembly_and_period_navigation(coordinator, final):
    comp = final["header"]["competitions"][0]
    entry = {"id": comp["id"], "date": comp["date"], "season": {"year": 2026}, "seasonType": {"type": 2}, "competitions": [comp]}
    async def fetch(url):
        return final if "/summary?" in url else {}
    coordinator._get_json = AsyncMock(side_effect=fetch)
    result = await coordinator._assemble_game_data([entry], comp["id"], comp["id"], "", "",
        {"team": {"displayName": "New York Knicks"}, "season": {"year": 2026}}, live_bridge=True)
    assert result.mode == "final" and result.current_period["number"] == 4
    assert result.featured_players["home"]["display_name"] == "OG Anunoby"
    assert result.situation["shot_clock"] is None
    middle = await coordinator.async_period_at_offset(-1)
    assert middle["current_period"]["number"] == 3
    assert (middle["away_score"], middle["home_score"]) == (87, 87)
    assert middle["period_context"]["display_clock"] == ""
    earliest = await coordinator.async_period_at_offset(-999)
    assert earliest["has_prev"] is False and earliest["total_periods"] == 4
    assert all(p["period"] == 1 for p in earliest["recent_plays"])


@pytest.mark.asyncio
async def test_core_new_quarter_clears_old_plays_before_summary_catches_up(coordinator, final):
    comp = final["header"]["competitions"][0]
    comp["status"] = competition(period=1)["status"]
    final["plays"] = [p for p in final["plays"] if p["period"]["number"] == 1]
    refreshed = competition(period=2)["status"]
    refreshed["displayClock"] = "12:00"
    async def fetch(url):
        if "/summary?" in url:
            return final
        if url.endswith("/status"):
            return refreshed
        if url.endswith("/situation"):
            return {"homeTimeouts": {"timeoutsRemainingCurrent": 5}}
        return {}
    coordinator._get_json = AsyncMock(side_effect=fetch)
    entry = {"id": comp["id"], "date": comp["date"], "season": {"year": 2026}, "seasonType": {"type": 2}, "competitions": [comp]}
    result = await coordinator._assemble_game_data([entry], comp["id"], "", "", comp["id"],
        {"team": {"displayName": "New York Knicks"}, "season": {"year": 2026}}, live_bridge=True)
    assert result.is_live is True and result.current_period["number"] == 2
    assert result.period_context["display_clock"] == "12:00"
    assert result.situation["home_timeouts"] == 5
    assert result.recent_plays == []


@pytest.mark.asyncio
async def test_double_overtime_navigation_rolls_back_to_first_overtime(coordinator, double_overtime):
    comp = double_overtime["header"]["competitions"][0]
    context = C._normalize_period_context(double_overtime, comp)
    coordinator._live_summary_cache = (comp["id"], double_overtime, context)
    earlier = await coordinator.async_period_at_offset(-1)
    assert earlier["period_context"]["display_period"] == "OT"
    assert earlier["away_score"] == earlier["home_score"]
    current = await coordinator.async_period_at_offset(0)
    assert current["period_context"]["display_period"] == "2OT"
    assert (current["away_score"], current["home_score"]) == (127, 134)
