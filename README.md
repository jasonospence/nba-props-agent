# NBA Props Agent MVP

## What it does
- pulls today's NBA events
- pulls player props
- looks at each target player's recent form
- scores prop candidates
- writes a daily report

## Setup
1. Create a virtual environment
2. Install dependencies:
   pip install -r requirements.txt
3. Copy `.env.example` to `.env`
4. Add your API keys
5. Run:
   python -m app.main

## Health check
Run a quick key + API connectivity check before the full pipeline:
```bash
python3 -m app.health_check
```

## Telegram delivery
To send the generated report to Telegram after each run, set these in `.env`:
```bash
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

Then run the pipeline:
```bash
python3 -m app.main
```

Optional run controls in `.env`:
```bash
ODDSLESS_MODE=false
MAX_PROPS_TO_PROCESS=0
PROGRESS_EVERY_N_PROPS=25
OPENAI_TIMEOUT_SECONDS=90
MAX_PLAYERS_PER_GAME=10
```
`MAX_PROPS_TO_PROCESS=0` means no cap (process full available props).
Report buckets: `Strong >= 70`, `Playable 50-69.9`, `Avoid < 50` (rejected rows are always shown in Avoid).
Set `ODDSLESS_MODE=true` to bypass Odds API completely and generate model props from BallDontLie only.

## Daily automation (11:00 AM Eastern)
Install a cron schedule to run every day at `11:00 AM America/New_York`:
```bash
chmod +x scripts/*.sh
./scripts/install_daily_schedule.sh
```

Run once manually:
```bash
./scripts/run_daily_report.sh
```

Remove the schedule:
```bash
./scripts/remove_daily_schedule.sh
```

Logs are written to:
```bash
outputs/logs/daily_runner.log
```

## GitHub Actions automation (runs when laptop is off)
This repo includes [daily-report.yml](/Users/jasonspence/nba-props-agent/.github/workflows/daily-report.yml), scheduled for **11:00 AM America/New_York** daily (DST-safe).

Setup in GitHub:
1. Push this repo to GitHub.
2. Go to `Settings -> Secrets and variables -> Actions`.
3. Add required **Secrets**:
   - `OPENAI_API_KEY`
   - `BALLDONTLIE_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Optional Secret:
   - `ODDS_API_KEY` (not needed if `ODDSLESS_MODE=true`)
5. Optional **Variables**:
   - `ODDSLESS_MODE` (`true` recommended)
   - `MAX_PROPS_TO_PROCESS`
   - `MAX_PLAYERS_PER_GAME`
   - `OPENAI_MODEL`
6. Enable Actions for the repo and run once via `Actions -> Daily NBA Props Report -> Run workflow`.

## Notes
- Injury parsing is stubbed in V1
- Use official NBA injury report logic next
- Start with points, rebounds, assists, threes only
- Do not auto-bet from V1 output

## Ball Dont Lie quick check
`BALLDONTLIE_API_KEY` is read from `.env`.

Example requests:
```bash
curl -H "Authorization: $BALLDONTLIE_API_KEY" "https://api.balldontlie.io/v1/games?per_page=100"
curl -H "Authorization: $BALLDONTLIE_API_KEY" "https://api.balldontlie.io/v1/players?search=lebron%20james&per_page=10"
curl -H "Authorization: $BALLDONTLIE_API_KEY" "https://api.balldontlie.io/v1/stats?player_ids[]=237&per_page=25"
curl -H "Authorization: $BALLDONTLIE_API_KEY" "https://api.balldontlie.io/v1/games?team_ids[]=14&per_page=10"
curl -H "Authorization: $BALLDONTLIE_API_KEY" "https://api.balldontlie.io/v1/injuries?player_name=lebron%20james&per_page=10"
```
