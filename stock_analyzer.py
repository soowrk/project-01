import asyncio
from datetime import datetime, timedelta

from pykrx import stock

# 국민연금이 주요 지분을 보유한 대표 종목 (정기적으로 업데이트 필요)
# 출처: 국민연금 공시 및 금융감독원 전자공시
NPS_HOLDINGS = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "035420": "NAVER",
    "005380": "현대자동차",
    "051910": "LG화학",
    "006400": "삼성SDI",
    "035720": "카카오",
    "105560": "KB금융",
    "055550": "신한지주",
    "086790": "하나금융지주",
    "316140": "우리금융지주",
    "003550": "LG",
    "017670": "SK텔레콤",
    "034730": "SK",
    "032830": "삼성생명",
    "010130": "고려아연",
    "009150": "삼성전기",
    "028260": "삼성물산",
    "066570": "LG전자",
    "000270": "기아",
    "012330": "현대모비스",
    "034020": "두산에너빌리티",
    "010950": "S-Oil",
    "011170": "롯데케미칼",
    "004020": "현대제철",
    "047050": "포스코인터내셔널",
    "003490": "대한항공",
    "069500": "KODEX 200",
    "036570": "엔씨소프트",
    "030200": "KT",
    "033780": "KT&G",
    "015760": "한국전력",
    "096770": "SK이노베이션",
    "018260": "삼성에스디에스",
    "021240": "코웨이",
    "011200": "HMM",
    "090430": "아모레퍼시픽",
    "004990": "롯데지주",
    "000810": "삼성화재",
}


def _get_trade_date(days_ago: int = 0) -> str:
    d = datetime.now() - timedelta(days=days_ago)
    return d.strftime("%Y%m%d")


def _safe_float(val, default=0.0):
    try:
        v = float(val)
        return v if v == v else default  # NaN check
    except (ValueError, TypeError):
        return default


async def get_nps_portfolio_summary() -> str:
    def _fetch():
        today = _get_trade_date()
        week_ago = _get_trade_date(7)
        lines = []
        top_tickers = list(NPS_HOLDINGS.keys())[:10]

        for ticker in top_tickers:
            try:
                df = stock.get_market_ohlcv(week_ago, today, ticker)
                if df.empty:
                    continue
                name = NPS_HOLDINGS[ticker]
                latest = df.iloc[-1]
                prev = df.iloc[0]
                price = int(latest["종가"])
                change_pct = ((latest["종가"] - prev["종가"]) / prev["종가"]) * 100
                emoji = "🔴" if change_pct < 0 else "🟢"
                lines.append(f"{emoji} {name}: {price:,}원 ({change_pct:+.1f}%)")
            except Exception:
                continue

        return "\n".join(lines) if lines else "데이터를 불러올 수 없습니다."

    return await asyncio.to_thread(_fetch)


async def find_undervalued_stocks() -> list[dict]:
    def _analyze():
        today = _get_trade_date()
        month_ago = _get_trade_date(30)
        results = []

        for ticker, name in NPS_HOLDINGS.items():
            try:
                df_ohlcv = stock.get_market_ohlcv(month_ago, today, ticker)
                if df_ohlcv.empty or len(df_ohlcv) < 5:
                    continue

                df_fundamental = stock.get_market_fundamental(today, today, ticker)
                if df_fundamental.empty:
                    continue

                per = _safe_float(df_fundamental.iloc[-1].get("PER"))
                pbr = _safe_float(df_fundamental.iloc[-1].get("PBR"))
                price = int(df_ohlcv.iloc[-1]["종가"])

                recent_vol = df_ohlcv["거래량"].iloc[-5:].mean()
                older_vol = df_ohlcv["거래량"].iloc[:-5].mean()

                if older_vol == 0:
                    continue

                vol_ratio = recent_vol / older_vol

                score = 0
                reasons = []

                if 0 < per <= 10:
                    score += 3
                    reasons.append(f"저PER({per:.1f})")
                elif 0 < per <= 15:
                    score += 1
                    reasons.append(f"적정PER({per:.1f})")

                if 0 < pbr <= 0.7:
                    score += 3
                    reasons.append(f"저PBR({pbr:.2f})")
                elif 0 < pbr <= 1.0:
                    score += 1
                    reasons.append(f"적정PBR({pbr:.2f})")

                if vol_ratio < 0.7:
                    score += 2
                    reasons.append("거래량 감소(관심↓)")

                price_high = df_ohlcv["고가"].max()
                discount = (price_high - price) / price_high * 100
                if discount > 20:
                    score += 2
                    reasons.append(f"고점 대비 {discount:.0f}%↓")

                if score >= 3 and reasons:
                    vol_change_str = f"{vol_ratio:.2f}x ({'감소' if vol_ratio < 1 else '증가'})"
                    results.append({
                        "ticker": ticker,
                        "name": name,
                        "price": price,
                        "per": f"{per:.1f}" if per > 0 else "N/A",
                        "pbr": f"{pbr:.2f}" if pbr > 0 else "N/A",
                        "volume_change": vol_change_str,
                        "reason": ", ".join(reasons),
                        "score": score,
                    })
            except Exception:
                continue

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:5]

    return await asyncio.to_thread(_analyze)
