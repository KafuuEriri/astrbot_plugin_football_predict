# AstrBot Football Lottery Paper Betting Plugin

[中文](README.md) | English

## Overview

This is an AstrBot plugin for simulated football lottery betting in group chats. It periodically fetches football match and odds data from a lottery API, caches the data into local CSV files, and lets group members check in daily for virtual currency before placing simulated bets on cached matches.

> This plugin is for entertainment and educational purposes only. It does not involve real-money transactions.

## Features

- Periodically fetch football matches and odds
- Cache data locally in CSV files; normal user commands do not call the API in real time
- Daily check-in grants 20,000 virtual credits
- Supports simulated Home/Draw/Away betting
- Locks cached odds when a bet is placed
- Supports bet cancellation, bet history, account summary, and group ranking
- Supports admin cache refresh, manual result entry, and settlement
- Core logic is covered by unit tests

## Installation

1. Place this plugin directory into your AstrBot plugins directory.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Enable the plugin in AstrBot.

## Configuration

Plugin configuration is defined in `_conf_schema.json`. Common options:

| Key | Default | Description |
| --- | ---: | --- |
| `fetch_interval_minutes` | `60` | Lottery API fetch interval in minutes |
| `settlement_interval_minutes` | `10` | Settlement scan interval in minutes |
| `days_ahead` | `7` | Number of future days to cache |
| `daily_checkin_amount` | `20000` | Daily check-in reward |
| `initial_balance` | `0` | Initial balance for new accounts |
| `min_bet_amount` | `100` | Minimum bet amount |
| `max_bet_amount` | `100000` | Maximum bet amount |
| `bet_close_minutes_before_match` | `5` | Betting and cancellation close N minutes before kickoff |
| `competition_keywords` | `世界杯,World Cup` | Competition filter keywords, comma-separated |
| `auto_fetch_on_start` | `true` | Fetch cache once on plugin startup |

## User Commands

| Command | Description |
| --- | --- |
| `/足球帮助` | Show help |
| `/足球签到` | Daily check-in |
| `/足球账户` | Show account balance and betting stats |
| `/世界杯赛事 [page]` | List cached World Cup matches open for betting |
| `/足球赔率 <match number or match_id>` | Show match odds |
| `/足球投注 <match number or match_id> <主胜|平|客胜> <amount>` | Place a simulated bet |
| `/足球撤单 <bet id>` | Cancel a pending bet before close time |
| `/我的投注 [未结|已结|page]` | Show bet history |
| `/足球排行` | Show current group ranking |

Examples:

```text
/足球签到
/世界杯赛事
/足球赔率 周五003
/足球投注 周五003 主胜 1000
/我的投注 未结
/足球排行
```

## Admin Commands

| Command | Description |
| --- | --- |
| `/足球刷新` | Manually refresh match cache |
| `/足球结算` | Manually run settlement |
| `/足球状态` | Show plugin status |
| `/足球录赛果 <match number or match_id> <主胜|平|客胜|无效> [score]` | Manually record match result |

Examples:

```text
/足球刷新
/足球录赛果 周五003 主胜 2-1
/足球结算
/足球状态
```

## Data Storage

Runtime data is stored in the AstrBot data directory:

```python
StarTools.get_data_dir("astrbot_plugin_football_predict")
```

Main files:

| File | Description |
| --- | --- |
| `matches.csv` | Latest match and odds cache |
| `odds_history.csv` | Odds snapshot history |
| `users.json` | User accounts |
| `bets.json` | Bet orders |
| `transactions.csv` | Balance transactions |
| `manual_results.csv` | Manually entered match results |
| `fetch_state.json` | Last fetch status |

## Testing

Run unit tests:

```bash
python3 -m unittest discover -s tests -v
```

Run syntax checks:

```bash
python3 -m compileall .
```

## Notes

- Normal user commands only read local cache and do not call the lottery API in real time.
- The lottery API may not reliably provide final match results, so manual admin result entry is supported.
- Bets are simulated and do not represent real lottery betting outcomes.
- Configure a reasonable fetch interval to avoid excessive API access.
