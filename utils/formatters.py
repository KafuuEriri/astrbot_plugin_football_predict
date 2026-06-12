from decimal import Decimal
from typing import Any, Dict, List

try:
    from models import BetOrder, LotteryMatch, UserAccount
    from utils.time_utils import format_ts
    from utils.validators import money_text
except ImportError:
    from ..models import BetOrder, LotteryMatch, UserAccount
    from .time_utils import format_ts
    from .validators import money_text


class Formatters:
    @staticmethod
    def help() -> str:
        return (
            "⚽ 体彩世界杯模拟投注\n"
            "━━━━━━━━━━━━\n"
            "📌 普通命令\n"
            "| 命令 | 用途 |\n"
            "| --- | --- |\n"
            "| /签到 | 每日领取20000虚拟币 |\n"
            "| /足球账户 | 查看余额和投注统计 |\n"
            "| /世界杯赛事 [页码/全部] | 查看缓存赛事 |\n"
            "| /足球赔率 <场次> | 查看单场赔率 |\n"
            "| /买球 阿根廷赢1000 | 简单自然语言下注 |\n"
            "| /足球投注 <场次> <主胜/平/客胜> <金额> | 精确下注 |\n"
            "| /足球撤单 <投注单号> | 停售前撤单 |\n"
            "| /我的投注 [未结/已结/页码] | 查看投注记录 |\n"
            "| /足球排行 | 当前群排行 |\n\n"
            "🛠 管理员：/足球刷新 /足球结算 /足球状态 /足球录赛果\n"
            "📦 普通命令只读取本地CSV缓存，不实时请求体彩接口。"
        )

    @staticmethod
    def checkin(created: bool, user: UserAccount, amount: Decimal) -> str:
        if created:
            return (
                "✅ 签到成功\n"
                f"💰 获得：{money_text(amount)}\n"
                f"🏦 当前余额：{money_text(user.balance)}\n"
                f"📅 累计签到：{user.checkin_count} 次"
            )
        return (
            "ℹ️ 今天已经签到过了\n"
            f"🏦 当前余额：{money_text(user.balance)}\n"
            f"📅 累计签到：{user.checkin_count} 次"
        )

    @staticmethod
    def account(summary: Dict[str, Any]) -> str:
        user = summary["user"]
        return (
            f"👤 足球账户：{user.username or user.sender_id}\n"
            "━━━━━━━━━━━━\n"
            f"🏦 余额：{money_text(user.balance)}\n"
            f"⏳ 未结投注：{summary['pending_count']} 单 / {money_text(summary['pending_stake'])}\n"
            f"📅 累计签到：{user.checkin_count} 次 / {money_text(user.total_checkin_amount)}\n"
            f"🎫 累计投注：{money_text(user.total_staked)}\n"
            f"💰 累计派彩：{money_text(user.total_payout)}\n"
            f"📊 战绩：✅{user.wins} / ❌{user.losses} / ↩️{user.voids} / 🚫{user.cancelled}"
        )

    @staticmethod
    def match_list(matches: List[LotteryMatch], page: int = 1, page_size: int = 8) -> str:
        if not matches:
            return "📭 暂无缓存的可投注世界杯赛事，请稍后等待后台刷新或联系管理员执行 /足球刷新。"
        total_pages = max(1, (len(matches) + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))
        start = (page - 1) * page_size
        lines = [f"🏆 世界杯赛事 第 {page}/{total_pages} 页", "━━━━━━━━━━━━"]
        for index, match in enumerate(matches[start:start + page_size], start=start + 1):
            pool = "不让球" if match.pool_type == "had" else f"让球({match.goal_line})"
            lines.extend([
                f"{index}. 🔢 {match.match_num or match.match_id}",
                f"   🆚 {match.home_team} vs {match.away_team}",
                f"   ⏰ {match.match_time}",
                f"   🎯 {pool}",
                f"   📊 主胜 {money_text(match.odds_h)} | 平 {money_text(match.odds_d)} | 客胜 {money_text(match.odds_a)}",
            ])
        lines.append("💡 简单下注：/买球 阿根廷赢1000")
        lines.append("💡 精确下注：/足球投注 场次 主胜 1000")
        return "\n".join(lines)

    @staticmethod
    def match_detail(match: LotteryMatch) -> str:
        pool = "不让球胜平负" if match.pool_type == "had" else f"让球胜平负({match.goal_line})"
        open_text = "✅ 可投注" if match.is_open_for_betting() else "⛔ 已停售"
        return (
            f"⚽ {match.display_name()}\n"
            "━━━━━━━━━━━━\n"
            f"🏆 赛事：{match.league_name}\n"
            f"⏰ 时间：{match.match_time}\n"
            f"🎯 玩法：{pool}\n"
            f"📊 赔率：主胜 {money_text(match.odds_h)} | 平 {money_text(match.odds_d)} | 客胜 {money_text(match.odds_a)}\n"
            f"⛔ 停售：{format_ts(match.sale_close_ts)}\n"
            f"📌 状态：{open_text}\n"
            f"📦 缓存：{format_ts(match.fetched_at)}"
        )

    @staticmethod
    def bet_created(bet: BetOrder) -> str:
        return (
            "✅ 投注成功\n"
            "━━━━━━━━━━━━\n"
            f"🎫 单号：{bet.bet_id}\n"
            f"⚽ 比赛：{bet.match_num} {bet.home_team} vs {bet.away_team}\n"
            f"🎯 选择：{bet.selection_text}\n"
            f"💵 金额：{money_text(bet.stake)}\n"
            f"📌 锁定赔率：{money_text(bet.odds_locked)}\n"
            f"💰 潜在返还：{money_text(bet.potential_payout)}"
        )

    @staticmethod
    def bet_cancelled(bet: BetOrder) -> str:
        return (
            "✅ 撤单成功\n"
            f"🎫 单号：{bet.bet_id}\n"
            f"↩️ 退回：{money_text(bet.stake)}"
        )

    @staticmethod
    def bet_history(bets: List[BetOrder], page: int = 1, page_size: int = 8) -> str:
        if not bets:
            return "📭 暂无投注记录。"
        total_pages = max(1, (len(bets) + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))
        start = (page - 1) * page_size
        lines = [f"🧾 我的投注 第 {page}/{total_pages} 页", "━━━━━━━━━━━━"]
        status_text = {"pending": "⏳未结", "won": "✅赢", "lost": "❌输", "void": "↩️无效", "cancelled": "🚫撤单"}
        lines.append("单号 | 状态 | 场次 | 选择 | 金额@赔率 | 返还")
        lines.append("--- | --- | --- | --- | --- | ---")
        for bet in bets[start:start + page_size]:
            lines.append(
                f"{bet.bet_id} | {status_text.get(bet.status, bet.status)} | {bet.match_num} | "
                f"{bet.selection_text} | {money_text(bet.stake)}@{money_text(bet.odds_locked)} | {money_text(bet.payout)}"
            )
        return "\n".join(lines)

    @staticmethod
    def ranking(rows: List[Dict[str, Any]]) -> str:
        if not rows:
            return "📭 当前群暂无账户数据。"
        lines = ["🏆 足球模拟投注排行榜", "━━━━━━━━━━━━", "排名 | 用户 | 资产 | 盈亏", "--- | --- | ---: | ---:"]
        for index, row in enumerate(rows[:10], start=1):
            user = row["user"]
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(index, str(index))
            lines.append(
                f"{medal} | {user.username or user.sender_id} | {money_text(row['net_assets'])} | {money_text(row['profit'])}"
            )
        return "\n".join(lines)

    @staticmethod
    def settlement_summary(summary: Dict[str, int]) -> str:
        return (
            "💰 结算完成\n"
            "━━━━━━━━━━━━\n"
            f"🔍 扫描：{summary.get('scanned', 0)} 单\n"
            f"✅ 结算：{summary.get('settled', 0)} 单\n"
            f"🏆 赢：{summary.get('won', 0)}｜❌ 输：{summary.get('lost', 0)}｜↩️ 无效：{summary.get('void', 0)}\n"
            f"⏳ 跳过：{summary.get('skipped', 0)} 单"
        )

    @staticmethod
    def natural_bet_usage() -> str:
        return (
            "💡 简单投注示例\n"
            "━━━━━━━━━━━━\n"
            "| 写法 | 示例 |\n"
            "| --- | --- |\n"
            "| 简单下注 | /买球 阿根廷赢1000 |\n"
            "| 带足球命令 | /足球投注 阿根廷赢1000 |\n"
            "| 精确下注 | /足球投注 周五003 主胜 1000 |"
        )

    @staticmethod
    def natural_bet_no_match(team_text: str) -> str:
        target = team_text or "该球队/场次"
        return (
            f"📭 未找到可投注赛事：{target}\n"
            "请先用 /世界杯赛事 查看未来两天赛事，或用 /世界杯赛事 全部 查看完整缓存。"
        )

    @staticmethod
    def natural_bet_candidates(team_text: str, matches: List[LotteryMatch]) -> str:
        lines = [f"🔎 找到多场包含“{team_text}”的赛事，请指定场次", "━━━━━━━━━━━━"]
        for match in matches[:8]:
            lines.append(f"🔢 {match.match_num or match.match_id}｜{match.home_team} vs {match.away_team}｜{match.match_time}")
        lines.append("💡 示例：/足球投注 周五003 主胜 1000")
        return "\n".join(lines)

    @staticmethod
    def status(fetch_state: Dict[str, Any], cached_count: int, pending_count: int) -> str:
        return (
            "📊 足球插件状态\n"
            "━━━━━━━━━━━━\n"
            f"📦 缓存赛事：{cached_count}\n"
            f"⏳ 未结投注：{pending_count}\n"
            f"🕒 最近抓取：{format_ts(int(fetch_state.get('last_fetch_at') or 0))}\n"
            f"✅ 抓取成功：{fetch_state.get('last_fetch_ok', '')}\n"
            f"⚠️ 最近错误：{fetch_state.get('last_error', '') or '无'}"
        )
