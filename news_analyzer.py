import os
import logging

from google import genai

logger = logging.getLogger(__name__)

client = None


def _get_client():
    global client
    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        client = genai.Client(api_key=api_key)
    return client


async def analyze_news(nps_news: list[dict], market_news: list[dict]) -> str | None:
    c = _get_client()
    if not c:
        logger.warning("GEMINI_API_KEY가 설정되지 않아 뉴스 분석을 건너뜁니다.")
        return None

    nps_text = "\n".join(
        f"- {n['title']}: {n['desc']}" for n in nps_news if n.get("title")
    )
    market_text = "\n".join(
        f"- {n['title']}: {n['desc']}" for n in market_news if n.get("title")
    )

    prompt = f"""당신은 한국 주식시장 전문 애널리스트입니다.
아래 뉴스들을 분석하여 개인 투자자에게 도움이 되는 간결한 리포트를 작성해주세요.

## 국민연금 관련 뉴스
{nps_text}

## 주식 시장 뉴스
{market_text}

다음 형식으로 작성해주세요:

📌 오늘의 핵심 요약 (3줄 이내)

🏛 국민연금 동향
- 국민연금의 최근 투자 움직임과 의미를 2-3줄로 요약

📈 시장 분석
- 오늘 주목할 시장 트렌드와 섹터를 2-3줄로 요약

💡 투자 인사이트
- 위 뉴스를 종합했을 때 개인 투자자가 주목할 포인트 2-3개

⚠️ 리스크 요인
- 주의해야 할 리스크 1-2개

짧고 핵심적으로 작성하세요. 이모지를 활용하세요."""

    try:
        response = c.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        logger.error(f"뉴스 분석 실패: {e}")
        return None
