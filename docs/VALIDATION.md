# v1.0.0 Release Validation

Validated September 3, 2026. This basketball adaptation follows the NFL/NHL siblings of @johnbr's MLB Live Scoreboard v1.28.2. NBA behavior was tested independently; sibling results were not used as proof.

## Automated checks

- All **118 Python** and **40 JavaScript** tests pass, together with repository-wide Ruff and JavaScript syntax checks.
- Coverage includes 30-team mapping, upcoming-season metadata, separate play-in schedules, four quarters, halftime, overtime/2OT, decimal countdown clocks, shooting statistics, DNP flags, traded-player aggregate season averages, and division-relative games behind.
- Scoring tests cover 1/2/3-point changes, combined free throws, first-load/reload baselines, score corrections and rebounds, same-basket two-to-three-point reviews, asynchronous play/score arrival, polling gaps, and final lifecycle actions.
- Card tests cover defaults/editor, missing data, expansion, leader/season/career tables, shot locations, stale asynchronous responses, navigation timers, focus restoration, and bounded newest-first histories.

Run locally:

```sh
python -m pip install pytest pytest-asyncio ruff
ruff check .
pytest tests/ -q
node --check custom_components/nba_live_scoreboard/nba-live-game-card.js
node --test tests/test_card.cjs
```

## Real Home Assistant acceptance

Tested in a disposable **Home Assistant 2026.9.0**, Python **3.14.3**, frontend **20260826.4**, bound only to localhost. The user's existing Home Assistant, dashboards, devices, and automations were not changed.

- Real team setup, invalid-team and duplicate-team rejection, and an available NBA sensor.
- Current public schedule selects **Knicks at 76ers, October 5, 2026, 7:00 PM Eastern**, event `401914101`.
- Options save/clear and a harmless test-only three-point action with real Home Assistant script variables.
- Automatic resource registration and exact-byte checks of both bundled card URLs; integration Python files are not publicly served.
- Authenticated game/period navigation and player career/season requests, including malformed athlete-ID rejection; Jalen Brunson's actual profile and season data load.
- Unload/reload without duplicate resources. NBA, NHL, and NFL run together with distinct sensors, card elements, and resources.
- Browser acceptance verifies three-digit scores, four-quarter linescores, scoring-leader portraits, court diagram, player career and team Game/Season popups, halftime leaders, final scoring/standings, and keyboard controls.
- The full regulation fixture exposes **132 fourth-quarter plays** and **120 scoring plays** in bounded scrolling panels. A historical-quarter view correctly shows the 87–87 third-quarter checkpoint without leaking the current clock or later scoring.
- Optional shot plotting shows **37 verified fourth-quarter locations**, with distinct made/missed and home/away markers. Free throws, invalid sentinels, malformed coordinates, and unknown-team locations are excluded.
- A **360px phone viewport** was visually checked, including three-digit scores, wrapped indivisible player-stat labels, court spacing, and the optional shot chart. The final scoring list accepts keyboard scrolling without collapsing the card.

Source games: Cleveland 111 at New York 119 (October 22, 2025); Indiana 137 at New York 134 in overtime (February 10, 2026 Eastern); Denver 127 at New York 134 in double overtime (February 4, 2026 Eastern). Live and halftime screens are explicitly labelled archived-data visual replays with final aggregate statistics, not second-by-second reconstructions.

Shot-coordinate orientation was verified against ESPN's [game chart](https://www.espn.com/nba/game/_/gameId/401809234/cavaliers-knicks) and its [primary frontend implementation](https://cdn1.espn.net/fitt-v3/ed5a90bc5707-2.0.5496/client/espnfitt/7469-808bf7bf.js). The mapping is team-relative, not inferred from period number.

## Limits

No currently live NBA broadcast was available for acceptance. ESPN interfaces are unofficial; latency, availability, and optional situations/coordinates vary. Missing possession and player-on-court information are not guessed. Season and career tables reflect available fetched regular-season per-game averages rather than historical snapshots.

HACS installs the tagged source tree as a **custom Integration repository** with its bundled card. A default-store listing is a separate review process and is not claimed. Installation still requires a Home Assistant restart, team setup, dashboard refresh, and adding the card.
