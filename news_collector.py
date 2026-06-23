import asyncio
import logging
from urllib.parse import quote

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

NPS_QUERIES = [
    "국민연금 주식투자",
    "국민연금 포트폴리오",
    "국민연금 지분 매수",
    "국민연금 보유 종목",
]

MARKET_QUERIES = [
    "코스피 전망",
    "미국 증시",
    "금리 인하 주식",
    "반도체 관련주",
    "2차전지 관련주",
    "AI 관련주 전망",
    "외국인 매수 종목",
    "기관 매수 종목",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


async def _fetch_naver_news(session: aiohttp.ClientSession, query: str) -> list[dict]:
    url = f"https://search.naver.com/search.naver?where=news&query={quote(query)}&sort=1"
    async with session.get(url, headers=HEADERS) as resp:
        if resp.status != 200:
            logger.warning(f"네이버 뉴스 검색 실패 (status {resp.status}): {query}")
            return []
        html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")
    articles = []

    for item in soup.select("div.news_area"):
        title_tag = item.select_one("a.news_tit")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        link = title_tag["href"]
        desc_tag = item.select_one("div.news_dsc")
        desc = desc_tag.get_text(strip=True) if desc_tag else ""
        articles.append({"title": title, "link": link, "desc": desc, "query": query})

    if not articles:
        for item in soup.select("a"):
            href = item.get("href", "")
            text = item.get_text(strip=True)
            if ("news" in href and len(text) > 15
                    and href.startswith("http")
                    and "search.naver" not in href):
                articles.append({"title": text, "link": href, "desc": "", "query": query})

    logger.info(f"[{query}] {len(articles)}건 수집")
    return articles


async def _fetch_google_news(session: aiohttp.ClientSession, query: str) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
    async with session.get(url, headers=HEADERS) as resp:
        if resp.status != 200:
            return []
        xml = await resp.text()

    soup = BeautifulSoup(xml, "html.parser")
    articles = []
    for item in soup.find_all("item"):
        title = item.find("title")
        link = item.find("link")
        if title and link:
            articles.append({
                "title": title.get_text(strip=True),
                "link": link.get_text(strip=True),
                "desc": "",
                "query": query,
            })
    logger.info(f"[Google][{query}] {len(articles)}건 수집")
    return articles


async def _collect(queries: list[str], limit: int) -> list[dict]:
    seen_titles = set()
    results = []

    async with aiohttp.ClientSession() as session:
        naver_tasks = [_fetch_naver_news(session, q) for q in queries]
        google_tasks = [_fetch_google_news(session, q) for q in queries]
        all_results = await asyncio.gather(*naver_tasks, *google_tasks)

    for articles in all_results:
        for a in articles:
            if a["title"] not in seen_titles:
                seen_titles.add(a["title"])
                results.append(a)

    return results[:limit]


async def collect_nps_news() -> list[dict]:
    return await _collect(NPS_QUERIES, 7)


async def collect_market_news() -> list[dict]:
    return await _collect(MARKET_QUERIES, 10)
