# NBA Live Scoreboard / GameTracker

This is an NBA-focused modified version of [MLB Live Scoreboard](https://github.com/johnbr/mlb-live-scoreboard), originally created by [@johnbr](https://github.com/johnbr). It follows the same adaptation and distribution approach as [NFL Live Scoreboard](https://github.com/julianrinaldi/nfl-live-scoreboard) and [NHL Live Scoreboard](https://github.com/julianrinaldi/nhl-live-scoreboard).

A Home Assistant custom integration and bundled Lovelace card for live NBA game data from ESPN.

[![HACS](https://img.shields.io/badge/HACS-Custom-blue.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=julianrinaldi&repository=nba-live-scoreboard&category=integration)
![Version](https://img.shields.io/github/v/release/julianrinaldi/nba-live-scoreboard?label=version&color=blue)

## Features

- **The same card experience** — compact score rows, expandable live/upcoming/final panels, team logos, responsive portraits, and a visual editor.
- **Basketball tracking** — points, four quarters, halftime, overtime, and basketball statistics.
- **Scoring-leader matchup** — each team's available points leader and statistics in the original two-player layout.
- **Quarter play-by-play** — scoring and foul indicators, quarter summaries, and navigation through earlier periods.
- **Game leaders** — points, rebounds, and assists during breaks and in final summaries.
- **Player career popup** — click a yellow player name for biography and season-by-season stats, or configure ESPN links.
- **Team stats popup** — click a team's matchup area to switch between Game and Season basketball tables.
- **NBA standings** — division standings with basketball records and games behind.
- **Game-event actions** — run Home Assistant actions for scores, game start/end, wins, and losses.
- **Bundled card** — automatic resource registration after integration setup; no separate card download.

Basketball fields replace baseball, football, and hockey concepts; unavailable feed data is not invented. See [Data Source](#data-source) and [validation notes](docs/VALIDATION.md).

## Installation

### HACS (Recommended)

This is a **custom Integration repository** for [HACS](https://hacs.xyz/), not a separate Dashboard download or a claimed default-store listing.

1. Open **HACS → ⋮ → Custom repositories**.
2. Add `https://github.com/julianrinaldi/nba-live-scoreboard` with category **Integration**.
3. Search for **NBA Live Scoreboard** and choose **Download**.
4. Restart Home Assistant.
5. Add your team under **Settings → Devices & Services → Add Integration → NBA Live Scoreboard**.
6. **Refresh your dashboard/browser** to load the newly registered card.
7. Edit your dashboard, choose **Add card**, and search for **NBA Live Game Card**.

[Open this repository in HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=julianrinaldi&repository=nba-live-scoreboard&category=integration).

Downloading in HACS alone does not configure a team or place a card on the dashboard. The card is included inside the integration, just like the original project.

### Manual Installation

1. Download a [release](https://github.com/julianrinaldi/nba-live-scoreboard/releases).
2. Copy `custom_components/nba_live_scoreboard` into Home Assistant's `config/custom_components/` folder.
3. Restart Home Assistant, add the integration, refresh the dashboard, and add the card as above.

Keep the folder name `nba_live_scoreboard`. NBA, NHL, NFL, and MLB have separate domains, resources, events, and card elements and can coexist.

## Configuration

### Integration Setup

Select a team such as `NY` for the New York Knicks and optionally set a display name. The sensor will be named like `sensor.nba_live_scoreboard_ny`. Add another integration entry for another team; duplicate entries for the same team are rejected. Team abbreviations follow ESPN, so the Knicks use `NY`, not `NYK`.

### Lovelace Card Setup

The card is registered as a **JavaScript Module**, with a version query string for browser cache updates:

```text
/hacsfiles/nba_live_scoreboard/nba-live-game-card.js
```

It also works for manual installations without HACS. If copying into `www/community` fails, the integration registers `/nba_live_scoreboard/nba-live-game-card.js` instead.

**Visual:** Edit dashboard → Add card → search **NBA Live Game Card**. Choose your NBA sensor and options.

**Equivalent YAML:**

```yaml
type: custom:nba-live-game-card
entity: sensor.nba_live_scoreboard_ny
```

If the card is missing from the picker, refresh the dashboard after setting up the integration. If automatic registration is unavailable, add the URL under **Settings → Dashboards → ⋮ → Resources**, with type **JavaScript Module**, then refresh. For YAML-managed resources, merge this into the existing list:

```yaml
lovelace:
  resources:
    - url: /hacsfiles/nba_live_scoreboard/nba-live-game-card.js?v=110
      type: module
```

Do not replace other resources or dashboards.

## Card Configuration Options

| Option | Default | Description |
| --- | --- | --- |
| `entity` | required | NBA scoreboard sensor |
| `title` | `""` | Upstream-compatible; no separate title heading is rendered |
| `refresh_rate` | `0` | Local repaint seconds; does not control feed polling |
| `show_within_hours` | `0` | Hide outside the next game's hours window; `0` or blank disables hiding. Live games always show. |
| `show_matchup` | `true` | Scoring-leader matchup or Game Leaders |
| `show_records` | `true` | Win-loss records on compact pregame/final cards |
| `show_linescore` | `false` | Quarter/overtime points in the expanded live view |
| `show_plays` | `true` | Current/selected period play-by-play |
| `show_play_results` | `true` | Points, foul, and shot indicators |
| `show_period_summary` | `true` | Selected-period summary |
| `show_possession` | `true` | Possession indicator only when explicitly identified by the feed |
| `show_court` | `true` | Compact basketball court diagram; does not infer a live ball position |
| `show_situation` | `true` | Available timeout counts and shot clock |
| `show_win_probability` | `true` | Probability bar when supplied by ESPN |
| `show_shot_chart` | `false` | Optional selected-period shot locations |
| `show_highlights` | `false` | ESPN highlights link when available |
| `player_link_target` | `popup` | `popup` or `espn` |
| `show_team_stats_popup` | `true` | Team Game/Season popup; player links remain independent |
| `team_stats_default_view` | `auto` | `auto`, `game`, or `season`; auto chooses Game live, Season otherwise |
| `show_schedule_nav` | `true` | Previous/upcoming game navigation |
| `show_period_nav` | `true` | Earlier-period navigation |
| `live_default_view` | `collapsed` | `collapsed` or `expanded` initial live layout |
| `headshot_size` | `auto` | `auto`, `small` (40px), `medium` (56px), `large` (72px), `xlarge` (88px) |

Expansion resets to the configured default for a new game. Schedule navigation returns to the automatically selected game after 60 seconds of inactivity; period navigation returns to the current period after 20 seconds.

Period plays and final scoring plays are newest-first inside keyboard-scrollable panels capped at 320px, keeping the dashboard compact while retaining the complete available history.

### Hide until the next game is close

In the visual card editor, set **Show only within (hours, 0 = always)** to `24` to hide the entire card until the team's next game is within 24 hours. You can also use YAML:

```yaml
type: custom:nba-live-game-card
entity: sensor.nba_live_scoreboard_ny
show_within_hours: 24
```

The boundary is inclusive and fractional hours are supported. Live games, including halftime and in-progress delays, stay visible. When a game finishes, the card hides unless the next game is already within the window. An available sensor with no upcoming game also hides; cancelled, postponed, and unconfirmed start times do not count. The rule uses the team's actual next game even when the card still displays a recent final or you browse the schedule.

Hidden cards keep receiving Home Assistant updates and check the clock automatically, even with `refresh_rate: 0`. No dashboard refresh or extra ESPN polling is needed. A just-starting game remains visible while the feed catches up; a stale scheduled status expires after six hours unless the feed confirms a live game. Editor previews and missing/unavailable-entity diagnostics remain visible so settings and connection problems can be fixed. Set `0`, clear the field, or remove the option to restore the existing always-visible behavior. Each card can have a different window.

After updating through HACS, restart Home Assistant and refresh the dashboard once to load the new integration and bundled card.

### Other display options

```yaml
type: custom:nba-live-game-card
entity: sensor.nba_live_scoreboard_ny
show_linescore: true
show_matchup: true
show_plays: true
show_period_nav: true
live_default_view: expanded
headshot_size: auto
```

## Game Event Actions

Under **Settings → Devices & Services → NBA Live Scoreboard → Configure**, assign action sequences to game events. Events are also fired on the event bus for separate automations.

| Event | Trigger |
| --- | --- |
| `nba_live_scoreboard_team_scored` | Your team's score increased |
| `nba_live_scoreboard_opponent_scored` | Opponent's score increased |
| `nba_live_scoreboard_game_started` | Game became live |
| `nba_live_scoreboard_game_ended` | Game became final |
| `nba_live_scoreboard_game_won` | Your team won |
| `nba_live_scoreboard_game_lost` | Your team lost |

Payloads include `team_abbr`, `team_name`, `team_score`, `opponent_abbr`, `opponent_name`, `opponent_score`, `is_home`, `period`, `clock`, `event_id`, and `status_detail`. Score events also include `score_delta` and available `scoring_play_text`.

The first refresh, a new game, and reload establish baselines without replaying celebrations. Live score increases of 1–3 points can trigger actions; this may combine free throws between polls. Corrections, score rebounds, jumps larger than 3 points, and polling gaps longer than 120 seconds are suppressed. Lifecycle events are de-duplicated. Actions concern the configured club only; game-ended and win/loss actions use the official final score.

### Event-triggered automation

```yaml
automation:
  - alias: "Notify when the Knicks score"
    triggers:
      - trigger: event
        event_type: nba_live_scoreboard_team_scored
        event_data:
          team_abbr: NY
    actions:
      - action: persistent_notification.create
        data:
          title: "Knicks scored!"
          message: "{{ trigger.event.data.scoring_play_text }}"
```

### Action configured in the integration options

For **When my team wins**:

```yaml
- action: persistent_notification.create
  data:
    title: "{{ team_name }} won!"
    message: "Final: {{ team_score }}-{{ opponent_score }} vs {{ opponent_name }}"
```

Options actions use top-level variables such as `team_score`; event automations use `trigger.event.data.team_score`.

## Sensor State Attributes

The state is the ESPN event ID, or `idle`. Attributes include `game_active`, `mode`, `is_live`, `status_text`, `competition`, `period_context`, `featured_players`, `situation`, `current_period`, `recent_plays`, `scoring_plays`, `team_stats`, `leaders`, and `division_standings`.

Live attributes are excluded from recorder history to avoid large, rapidly changing records. The card reads current state directly.

To show a card only while a game is active, create a Template Binary Sensor helper:

```jinja
{{ state_attr('sensor.nba_live_scoreboard_ny', 'game_active') == true }}
```

Use that helper's `on` state in your conditional-card settings.

## Supported Teams

All 30 NBA teams, using ESPN abbreviations:

| Abbreviation | Team | Abbreviation | Team |
| --- | --- | --- | --- |
| ATL | Atlanta Hawks | BOS | Boston Celtics |
| BKN | Brooklyn Nets | CHA | Charlotte Hornets |
| CHI | Chicago Bulls | CLE | Cleveland Cavaliers |
| DAL | Dallas Mavericks | DEN | Denver Nuggets |
| DET | Detroit Pistons | GS | Golden State Warriors |
| HOU | Houston Rockets | IND | Indiana Pacers |
| LAC | LA Clippers | LAL | Los Angeles Lakers |
| MEM | Memphis Grizzlies | MIA | Miami Heat |
| MIL | Milwaukee Bucks | MIN | Minnesota Timberwolves |
| NO | New Orleans Pelicans | NY | New York Knicks |
| OKC | Oklahoma City Thunder | ORL | Orlando Magic |
| PHI | Philadelphia 76ers | PHX | Phoenix Suns |
| POR | Portland Trail Blazers | SAC | Sacramento Kings |
| SA | San Antonio Spurs | TOR | Toronto Raptors |
| UTAH | Utah Jazz | WSH | Washington Wizards |

## Data Source

Uses unauthenticated [ESPN NBA feeds](https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard). No account or API key is required. These interfaces are **unofficial and undocumented**, not a supported ESPN contract; availability and formats can change.

Polling is every **5 seconds** live, **30 seconds** near a game, and **5 minutes** idle. Broadcast synchronization is not guaranteed. Missing situation, coordinate, possession, or probability fields remain absent rather than guessed.

Schedules combine available preseason, regular-season, play-in, and postseason feeds. A previous result is preferred until 16 hours after scheduled start, then the next game is selected. Navigation is limited to returned events, not an unlimited archive. All-Star/international games do not replace your selected club's games.

Game statistics belong to the selected event. Season/career tables show available **regular-season per-game averages** when fetched, not season totals or historical snapshots. Featured players are available game scoring leaders, not a prediction of the starting lineup or proof of who is currently on the court. Pregame scoring-leader fields can therefore remain empty.

## Development and Validation

See [ARCHITECTURE.md](ARCHITECTURE.md) and [docs/VALIDATION.md](docs/VALIDATION.md). Workflows retain Tests, Hassfest, HACS validation, and release-please.

```sh
python -m pip install pytest pytest-asyncio ruff
ruff check .
pytest tests/ -q
node --check custom_components/nba_live_scoreboard/nba-live-game-card.js
node --test tests/test_card.cjs
```

## License and Attribution

Based on [MLB Live Scoreboard](https://github.com/johnbr/mlb-live-scoreboard) by [@johnbr](https://github.com/johnbr), v1.28.2, commit `acda998cef7d9e8614d4f9a62be7dbb7645e68f4`, through the [NFL](https://github.com/julianrinaldi/nfl-live-scoreboard) and [NHL](https://github.com/julianrinaldi/nhl-live-scoreboard) adaptations. The original [MIT license](LICENSE) is preserved.

NBA versions start independently at `1.0.0`. Team/league marks and player imagery belong to their owners. This community project is not affiliated with or endorsed by the NBA, ESPN, Home Assistant, or HACS.
