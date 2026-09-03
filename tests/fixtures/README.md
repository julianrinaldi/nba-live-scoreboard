# NBA ESPN regression fixtures

Public ESPN responses captured September 3, 2026. Tests run offline. Retained
fields preserve actual API structure, identifiers, dates, scores, and statistics.

| Fixture | Verified source content |
| --- | --- |
| `summary_401809234_regulation.json` | Cleveland at New York, October 22, 2025, 23:00 UTC; final CLE 111, NY 119 |
| `summary_401810626_overtime.json` | Indiana at New York, February 11, 2026, 00:30 UTC; final IND 137, NY 134 in overtime |
| `summary_401810581_double_overtime.json` | Denver at New York, February 5, 2026, 00:00 UTC; final DEN 127, NY 134 in double overtime |
| `athlete_3934672_bio.json`, `athlete_3934672_stats.json` | Jalen Brunson, guard; latest retained regular season 2025–26 |
| `teams_20260903.json` | All 30 NBA teams and canonical ESPN abbreviations, including NY, GS, NO, SA, and UTAH |
| `groups_20260903.json` | Two conferences, six divisions, and team membership |
| `standings_atlantic_2026.json` | Actual 2025–26 BOS, PHI, and NY rows from Eastern Conference standings |
| `schedule_ny_default_20260903.json` | First and last of five upcoming NY preseason games; starts October 5, 2026, 23:00 UTC, event 401914101 |
| `schedule_ny_regular_2026.json` | Selected 2025–26 NY regular-season games, preserving generic season 2027 metadata versus requested/event season 2026 |
| `schedule_phi_playin_2026.json` | Separate phase-5 Orlando at Philadelphia play-in game, April 15, 2026, 23:30 UTC, event 401866757 |
| `schedule_phi_postseason_2026.json` | First and last PHI phase-3 postseason games; this response omits the earlier phase-5 play-in game |

## Primary source endpoints

- Game: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={EVENT_ID}`
- Teams: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams?limit=100`
- Divisions: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/groups`
- Standings: `https://site.api.espn.com/apis/v2/sports/basketball/nba/standings?season=2026&seasontype=2`
- Biography: `https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/3934672?region=us&lang=en`
- Player statistics: `https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/3934672/stats?region=us&lang=en`
- Current NY schedule: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/ny/schedule`
- Historical NY schedule: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/ny/schedule?season=2026&seasontype=2`
- PHI play-in schedule: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/phi/schedule?season=2026&seasontype=5`
- PHI postseason schedule: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/phi/schedule?season=2026&seasontype=3`
- Shot-chart transform: `https://cdn1.espn.net/fitt-v3/ed5a90bc5707-2.0.5496/client/espnfitt/7469-808bf7bf.js` (ESPN's own `ShotChartCourt` implementation)

## Trimming and test boundaries

Summaries retain all scoring plays and period boundaries, the first 12 plays,
selected fouls/timeouts/substitutions, final plays, all box-score player rows,
team statistics, leaders, competition headers, period scores, game format,
and the final two win-probability entries. They contain 150, 173, and 173 plays,
respectively; these are not complete play-by-play archives. News, media,
redundant logos, large descriptions, and link metadata are removed.

Player statistics retain all category schemas, career totals, glossary, team
lookup, and the most recent two season rows. Biography keeps profile fields.
Schedule fixtures preserve metadata and selected event identity/date/status
fields; the PHI fixtures contain identity and season fields only.

Live, halftime, quarter breaks, delayed/postponed games, missing data, malformed
input, reviewed shots, and asynchronous feed ordering are explicitly simulated
tests. They are not claimed to be captures of currently live games.

## Verified basketball semantics

- Four regulation quarters are 12 minutes each; overtime periods are 5 minutes.
  Play clocks count down, including decimal seconds such as `1.1` and `0.0`.
- Period 5 is OT and period 6 is 2OT. NBA games never have a shootout.
- Scoring plays carry one, two, or three points. Quarter point totals from
  retained scoring plays match the captured official linescores.
- A player row may contain `reason: COACH'S DECISION` while `didNotPlay` is
  false and actual statistics exist. Only the explicit DNP flag is decisive.
- Player season categories are `averages`, `totals`, and `miscellaneous`.
  Per-game averages must not be replaced with season totals.
- Leader athletes can carry their later/current team identity. The enclosing
  game leader team's identity determines the side for the archived game.
- Free-throw and non-shot coordinates may contain invalid sentinel values
  such as -214748340 and -214748365; these must never appear as court markers.
- ESPN's court transform is bottom = x / 50 and left = (y + 4) / 94, with
  both reversed for home-team shots. Tests verify actual away (26, 12) and
  home (48, 0) shots, finite bounds, team identity, and free-throw exclusion.
- Play-in games use season phase 5 and are absent from phase-3 postseason
  responses. Both phases must be fetched when building the complete schedule.
- Generic season metadata can differ from requested season and event years.
  Tests include missing/stale requested metadata as explicit mutations.
- ESPN's source games-behind figure is relative to the conference leader.
  A division table must compute its own games behind from actual W/L records.
