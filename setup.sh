#!/bin/bash
set -e

echo "=== 국민연금 투자 텔레그램 봇 설치 ==="
echo ""

# Python 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3이 설치되어 있지 않습니다."
    echo "   https://www.python.org/downloads/ 에서 설치해주세요."
    exit 1
fi

echo "✅ Python3: $(python3 --version)"

# 가상환경 생성
if [ ! -d ".venv" ]; then
    echo "📦 가상환경 생성 중..."
    python3 -m venv .venv
fi

# 가상환경 활성화
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

echo "📦 패키지 설치 중..."
pip install -q -r requirements.txt

# .env 파일 확인
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  .env 파일이 생성되었습니다."
    echo "   아래 정보를 입력해주세요:"
    echo ""
    read -p "   텔레그램 봇 토큰: " bot_token
    read -p "   텔레그램 채팅 ID: " chat_id
    sed -i.bak "s/your_telegram_bot_token_here/$bot_token/" .env
    sed -i.bak "s/your_chat_id_here/$chat_id/" .env
    rm -f .env.bak
fi

echo ""
echo "✅ 설치 완료!"
echo ""
echo "실행 방법:"
echo "  source .venv/bin/activate"
echo "  python bot.py"
echo ""
echo "백그라운드 실행:"
echo "  nohup python bot.py > bot.log 2>&1 &"
