# Architecture

A basketball adaptation of the original MLB card through the NFL and NHL siblings. Distribution remains a HACS **Integration** with a bundled JavaScript card.

## Components

- `config_flow.py`: one team per entry, duplicate rejection, six configurable game-event actions.
- `coordinator.py`: ESPN data, bounded caches, schedule selection, basketball normalization, navigation, events.
- `const.py` / `types.py`: verified team IDs, polling policies, card-facing shapes.
- `sensor.py`: event ID and normalized attributes; large live payloads excluded from recorder.
- `__init__.py`: setup/unload, exact-file static routes, resource registration, authenticated WebSockets.
- `nba-live-game-card.js`: scoreboards, scoring/game leaders, quarter plays, court/shot display, standings, popups, editor.

## Data flow

The coordinator selects a club's live game, recent final, or upcoming event and combines its summary with team, roster, standings, and player data. The sensor and game navigation use the same attribute builder. Period browsing changes only the requesting card, never the live sensor or event actions.

WebSocket commands under `nba_live_scoreboard`: `game_at_offset`, `period_at_offset`, `player_card`, `team_season_stats`. Entity navigation resolves the correct config entry. Athlete IDs and batch sizes are validated. Player strings are escaped; optional fields remain absent instead of invented.

## Basketball semantics

Four 12-minute regulation quarters precede five-minute overtime periods. Period 5 is OT, period 6 is 2OT, and later periods continue accordingly. Points, rebounds, assists, field goals, three-pointers, free throws, turnovers, and personal fouls use basketball fields. There are no hockey shootouts or overtime-loss records.

Optional possession, timeouts, shot clock, and coordinates render only when available. A featured player is an actual game scoring leader, not a confirmed starter or active-on-court indicator. Season/career tables are current fetched data, not historical snapshots.

## Lifecycle and coexistence

Setup copies the module into `www/community/nba_live_scoreboard` when writable and registers its versioned `/hacsfiles/nba_live_scoreboard/nba-live-game-card.js` URL. An exact-file fallback at `/nba_live_scoreboard/nba-live-game-card.js` also works; Python source directories are not exposed.

Storage-managed resources are created/updated; YAML-managed resources need manual setup. Refresh the browser after setup to load the module. No dashboard cards are automatically placed. MLB/NFL/NHL/NBA have separate domains, elements, popup caches/styles, resources, and event names.

## Event safety

First refresh/reload and new games establish baselines. Scores must be present and plausible; corrections, rebounds, and stale gaps do not replay celebrations. Lifecycle events are de-duplicated. Options actions use Home Assistant's script validation and expose event fields as template variables.

## Tests and releases

Python/Node tests cover normalization, caching, events, card rendering, navigation, and registration. Real HA testing is separate; import-stub tests do not prove installation success.

HACS installs the tagged source tree. Workflows: Tests, Hassfest, HACS Integration validation, release-please. Versions live in the manifest, release-please manifest, and marked card version. Tags start at `v1.0.0`. The original MIT notice and @johnbr attribution remain.
