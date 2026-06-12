# AstrBot 体彩世界杯模拟投注插件 / AstrBot Football Lottery Paper Betting Plugin

## 简介 / Overview

这是一个 AstrBot 插件，用于在群聊中模拟体彩足球世界杯投注。插件会定期通过彩票接口获取足球赛事和赔率，将数据缓存到本地 CSV 文件；群成员通过每日签到领取虚拟币，并基于缓存赛事进行模拟下注。

This is an AstrBot plugin for simulated football lottery betting in group chats. It periodically fetches football match and odds data from the China Sports Lottery API, caches the data into local CSV files, and lets group members check in daily for virtual currency before placing simulated bets on cached matches.

> 本插件仅用于娱乐和学习，不涉及真实金钱交易。  
> This plugin is for entertainment and educational purposes only. It does not involve real-money transactions.

## 功能 / Features

- 定期抓取体彩足球赛事和赔率  
  Periodically fetch China Sports Lottery football matches and odds
- 本地 CSV 缓存，普通用户命令不实时请求接口  
  Local CSV cache; normal user commands do not trigger real-time API requests
- 群成员每日签到领取 20000 虚拟币  
  Daily check-in grants 20,000 virtual credits
- 支持主胜、平、客胜模拟投注  
  Supports simulated Home/Draw/Away betting
- 下注时锁定当前缓存赔率  
  Locks cached odds when a bet is placed
- 支持撤单、投注记录、账户查询和群内排行  
  Supports cancellation, bet history, account summary, and group ranking
- 支持管理员刷新赛事、录入赛果和手动结算  
  Supports admin match refresh, manual result entry, and settlement
- 核心逻辑配套单元测试  
  Core logic is covered by unit tests

## 安装 / Installation

1. 将插件目录放入 AstrBot 插件目录。  
   Place this plugin directory into your AstrBot plugins directory.

2. 安装依赖：  
   Install dependencies:

```bash
pip install -r requirements.txt
```

3. 在 AstrBot 中启用插件。  
   Enable the plugin in AstrBot.

## 配置 / Configuration

插件配置见 `_conf_schema.json`。常用配置：  
Plugin configuration is defined in `_conf_schema.json`. Common options:

| 配置 / Key | 默认值 / Default | 说明 / Description |
| --- | ---: | --- |
| `fetch_interval_minutes` | `60` | 体彩接口抓取间隔 / API fetch interval in minutes |
| `settlement_interval_minutes` | `10` | 结算扫描间隔 / Settlement scan interval in minutes |
| `days_ahead` | `7` | 缓存未来赛事天数 / Number of future days to cache |
| `daily_checkin_amount` | `20000` | 每日签到金额 / Daily check-in reward |
| `initial_balance` | `0` | 新账户初始余额 / Initial balance for new accounts |
| `min_bet_amount` | `100` | 单笔最小投注 / Minimum bet amount |
| `max_bet_amount` | `100000` | 单笔最大投注 / Maximum bet amount |
| `bet_close_minutes_before_match` | `5` | 开赛前停售分钟数 / Betting closes N minutes before kickoff |
| `competition_keywords` | `世界杯,World Cup` | 赛事过滤关键词 / Competition filter keywords |
| `auto_fetch_on_start` | `true` | 启动时自动刷新 / Fetch once on startup |

## 用户命令 / User Commands

| 命令 / Command | 说明 / Description |
| --- | --- |
| `/足球帮助` | 查看帮助 / Show help |
| `/足球签到` | 每日签到领取虚拟币 / Daily check-in |
| `/足球账户` | 查看账户余额和统计 / Show account summary |
| `/世界杯赛事 [页码]` | 查看缓存赛事 / List cached World Cup matches |
| `/足球赔率 <场次编号或match_id>` | 查看单场赔率 / Show match odds |
| `/足球投注 <场次编号或match_id> <主胜|平|客胜> <金额>` | 模拟下注 / Place a simulated bet |
| `/足球撤单 <投注单号>` | 停售前撤单 / Cancel a pending bet before close time |
| `/我的投注 [未结|已结|页码]` | 查看投注记录 / Show bet history |
| `/足球排行` | 查看当前群排行 / Show group ranking |

示例 / Examples:

```text
/足球签到
/世界杯赛事
/足球赔率 周五003
/足球投注 周五003 主胜 1000
/我的投注 未结
/足球排行
```

## 管理员命令 / Admin Commands

| 命令 / Command | 说明 / Description |
| --- | --- |
| `/足球刷新` | 手动刷新体彩缓存 / Manually refresh lottery cache |
| `/足球结算` | 手动执行结算 / Manually run settlement |
| `/足球状态` | 查看插件状态 / Show plugin status |
| `/足球录赛果 <场次编号或match_id> <主胜|平|客胜|无效> [比分]` | 手动录入赛果 / Manually record match result |

示例 / Examples:

```text
/足球刷新
/足球录赛果 周五003 主胜 2-1
/足球结算
/足球状态
```

## 数据存储 / Data Storage

插件运行数据保存在 AstrBot 数据目录中：  
Runtime data is stored in the AstrBot data directory:

```python
StarTools.get_data_dir("astrbot_plugin_football_predict")
```

主要文件 / Main files:

| 文件 / File | 说明 / Description |
| --- | --- |
| `matches.csv` | 最新赛事和赔率缓存 / Latest match and odds cache |
| `odds_history.csv` | 赔率快照历史 / Odds snapshot history |
| `users.json` | 用户账户 / User accounts |
| `bets.json` | 投注订单 / Bet orders |
| `transactions.csv` | 余额流水 / Balance transactions |
| `manual_results.csv` | 管理员手动赛果 / Manually entered results |
| `fetch_state.json` | 最近抓取状态 / Last fetch status |

## 测试 / Testing

运行单元测试：  
Run unit tests:

```bash
python3 -m unittest discover -s tests -v
```

运行语法检查：  
Run syntax checks:

```bash
python3 -m compileall .
```

## 注意事项 / Notes

- 普通用户命令只读取本地缓存，不会实时请求体彩接口。  
  Normal user commands only read local cache and do not call the lottery API in real time.
- 体彩接口可能不稳定提供最终赛果，因此保留管理员手动录入赛果功能。  
  The lottery API may not reliably provide final match results, so manual admin result entry is supported.
- 投注为虚拟模拟，不代表真实体彩投注结果。  
  Bets are simulated and do not represent real lottery betting outcomes.
- 请合理设置抓取间隔，避免频繁访问接口。  
  Configure a reasonable fetch interval to avoid excessive API access.
