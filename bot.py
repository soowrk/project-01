import os
import asyncio
import logging
from datetime import datetime, time

from dotenv import load_dotenv
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from news_collector import collect_nps_news, collect_market_news
from news_analyzer import analyze_news
from stock_analyzer import find_undervalued_stocks, get_nps_portfolio_summary

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


async def build_daily_report() -> str:
    sections = []
    today = datetime.now().strftime("%Y-%m-%d")
    sections.append(f"📊 *국민연금 투자 데일리 리포트*\n📅 {today}\n")

    try:
        portfolio = await get_nps_portfolio_summary()
        sections.append(f"━━━━━━━━━━━━━━━━━━━━\n🏛 *국민연금 포트폴리오 요약*\n{portfolio}")
    except Exception as e:
        logger.error(f"포트폴리오 요약 실패: {e}")

    news = []
    market = []

    try:
        news = await collect_nps_news()
        if news:
            news_text = "\n".join(f"• [{n['title']}]({n['link']})" for n in news[:7])
            sections.append(f"━━━━━━━━━━━━━━━━━━━━\n📰 *국민연금 투자 뉴스*\n{news_text}")
        else:
            sections.append("━━━━━━━━━━━━━━━━━━━━\n📰 *국민연금 투자 뉴스*\n오늘 관련 뉴스가 없습니다.")
    except Exception as e:
        logger.error(f"뉴스 수집 실패: {e}")

    try:
        market = await collect_market_news()
        logger.info(f"시장 뉴스 수집 결과: {len(market)}건")
        if market:
            market_text = "\n".join(f"• [{n['title']}]({n['link']})" for n in market[:10])
            sections.append(f"━━━━━━━━━━━━━━━━━━━━\n📈 *주식 시장 주요 뉴스*\n{market_text}")
        else:
            sections.append("━━━━━━━━━━━━━━━━━━━━\n📈 *주식 시장 주요 뉴스*\n오늘 관련 뉴스가 없습니다.")
    except Exception as e:
        logger.error(f"시장 뉴스 수집 실패: {e}", exc_info=True)

    if news or market:
        try:
            analysis = await analyze_news(news, market)
            if analysis:
                sections.append(f"━━━━━━━━━━━━━━━━━━━━\n🤖 *AI 뉴스 분석 리포트*\n{analysis}")
        except Exception as e:
            logger.error(f"AI 분석 실패: {e}")

    try:
        picks = await find_undervalued_stocks()
        if picks:
            picks_text = "\n\n".join(
                f"🔹 *{s['name']}* ({s['ticker']})\n"
                f"   현재가: {s['price']:,}원 | PER: {s['per']} | PBR: {s['pbr']}\n"
                f"   거래량 변화: {s['volume_change']}\n"
                f"   💡 {s['reason']}"
                for s in picks[:5]
            )
            sections.append(f"━━━━━━━━━━━━━━━━━━━━\n💎 *저평가 관심 종목 (국민연금 보유)*\n{picks_text}")
    except Exception as e:
        logger.error(f"종목 분석 실패: {e}")

    sections.append("\n_본 리포트는 참고용이며 투자 판단의 책임은 본인에게 있습니다._")
    return "\n\n".join(sections)


async def send_message(bot: Bot, text: str):
    MAX_LEN = 4096
    for i in range(0, len(text), MAX_LEN):
        await bot.send_message(
            chat_id=CHAT_ID,
            text=text[i : i + MAX_LEN],
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )


async def send_daily_report():
    logger.info("데일리 리포트 생성 시작")
    bot = Bot(token=BOT_TOKEN)
    report = await build_daily_report()

    parts = report.split("━━━━━━━━━━━━━━━━━━━━")
    for part in parts:
        part = part.strip()
        if part:
            await send_message(bot, part)
    logger.info("데일리 리포트 전송 완료")


async def main():
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
    scheduler.add_job(send_daily_report, "cron", hour=8, minute=0)
    scheduler.start()
    logger.info("봇 시작됨 — 매일 오전 8시(KST)에 리포트를 전송합니다.")

    # 첫 실행 시 즉시 리포트 전송 (테스트용)
    await send_daily_report()

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
