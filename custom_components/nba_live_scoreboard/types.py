"""Documented card-facing data shapes; missing ESPN fields remain optional."""

from __future__ import annotations

from typing import Any, TypedDict


class TeamMetadata(TypedDict, total=False):
    id: str
    abbreviation: str
    name: str
    short_name: str
    logo: str
    record_summary: str


class PeriodContext(TypedDict, total=False):
    period: int
    display_period: str
    display_clock: str
    period_prefix: str
    label: str
    is_intermission: bool
    is_halftime: bool
    is_end_period: bool
    is_overtime: bool


class Situation(TypedDict, total=False):
    possession_team_id: str
    away_timeouts: int | None
    home_timeouts: int | None
    shot_clock: float | None


class FeaturedPlayerStats(TypedDict, total=False):
    points: str
    rebounds: str
    assists: str
    steals: str
    blocks: str
    field_goals: str
    three_pointers: str
    free_throws: str
    minutes: str
    season: str


class FeaturedPlayer(TypedDict, total=False):
    id: str
    display_name: str
    short_name: str
    headshot: str
    team_id: str
    game_stats: FeaturedPlayerStats
    season_stats: FeaturedPlayerStats
    source: str


class FeaturedPlayers(TypedDict, total=False):
    away: FeaturedPlayer
    home: FeaturedPlayer


class RecentPlay(TypedDict, total=False):
    id: str
    text: str
    away_score: int | None
    home_score: int | None
    wallclock_ts: float | None
    scoring_play: bool
    score_value: int
    play_type: str
    abbreviation: str
    period: int
    clock: str
    team_id: str
    is_foul: bool
    is_turnover: bool
    is_shot: bool
    is_free_throw: bool
    coordinate: dict[str, float]
    shot_type: str
    points_attempted: int | None


class ScoringPlay(TypedDict, total=False):
    id: str
    text: str
    period_type: str
    period_number: int
    period: int
    clock: str
    away_score: int | None
    home_score: int | None
    score_value: int
    team_id: str
    play_type: str
    abbreviation: str


class GamePeriod(TypedDict, total=False):
    id: str
    number: int
    label: str
    description: str
    play_count: int
    points: int
    away_points: int | None
    home_points: int | None
    is_current: bool


class TeamStatsRow(TypedDict, total=False):
    id: str
    name: str
    short_name: str
    position: str
    jersey: str
    headshot: str
    stats: list[str]
    starter: bool | None
    did_not_play: bool | None


class TeamStatsCategory(TypedDict, total=False):
    name: str
    label: str
    columns: list[str]
    keys: list[str]
    descriptions: list[str]
    totals: list[str]
    rows: list[TeamStatsRow]


class TeamStatsSide(TypedDict, total=False):
    team_id: str
    abbreviation: str
    name: str
    short_name: str
    logo: str
    source: str
    categories: list[TeamStatsCategory]


class TeamStats(TypedDict, total=False):
    away: TeamStatsSide
    home: TeamStatsSide


class LeaderEntry(TypedDict, total=False):
    category: str
    value: str
    name: str
    id: str
    headshot: str


class Leaders(TypedDict, total=False):
    away: list[LeaderEntry]
    home: list[LeaderEntry]


class WinProbability(TypedDict, total=False):
    home: float
    away: float
    tie: float


class StandingsEntry(TypedDict, total=False):
    team_id: str
    team_name: str
    team_short_name: str
    wins: str
    losses: str
    win_percent: str
    games_behind: str
    streak: str


class Standings(TypedDict, total=False):
    division_name: str
    entries: list[StandingsEntry]


class PlayerCardBio(TypedDict, total=False):
    name: str
    team: str
    position: str
    height: str
    weight: str
    age: str
    jersey: str
    headshot: str
    draft: str
    college: str
    experience: str
    hometown: str


class PlayerCareerSeason(TypedDict, total=False):
    year: str
    team: str
    stats: list[str]


class PlayerCareerTable(TypedDict, total=False):
    kind: str
    label: str
    columns: list[str]
    keys: list[str]
    seasons: list[PlayerCareerSeason]
    totals: list[str]


class PlayerCard(TypedDict, total=False):
    id: str
    bio: PlayerCardBio
    career: PlayerCareerTable
    glossary: dict[str, str]


Competition = dict[str, Any]
