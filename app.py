import requests
import re
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="이유나PB의 모닝브리프", layout="wide")

TICKERS = {
    "Nasdaq": "^IXIC",
    "S&P500": "^GSPC",
    "VIX": "^VIX",
    "미국채10Y": "^TNX",
    "달러인덱스": "DX-Y.NYB",
    "WTI": "CL=F",
    "Gold": "GC=F",
    "원달러": "KRW=X",
}

@st.cache_data(ttl=1800)
def get_snapshot(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="5d")

        if hist.empty or len(hist) < 2:
            return None, None, None

        close = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2])
        change = close - prev
        pct = (change / prev) * 100

        return close, change, pct

    except:
        return None, None, None


@st.cache_data(ttl=1800)
@st.cache_data(ttl=1800)
def get_korea_market():
    def get_naver_index(code):
        import requests, re

        url = f"https://finance.naver.com/sise/sise_index.naver?code={code}"
        headers = {"User-Agent": "Mozilla/5.0"}

        html = requests.get(url, headers=headers).text

        value_match = re.search(r'id="now_value">([\d,\.]+)</em>', html)
        change_match = re.search(r'id="change_value_and_rate">(.*?)</span>', html, re.S)

        if not value_match:
            return None, None

        value = float(value_match.group(1).replace(",", ""))

        change = 0.0
        if change_match:
            text = re.sub("<.*?>", "", change_match.group(1)).strip()
            nums = re.findall(r"[\d,\.]+", text)

            if nums:
                change = float(nums[0].replace(",", ""))

            if "하락" in text:
                change = -change

        return value, change

    try:
        kospi_close, kospi_change, _ = get_snapshot("^KS11")
        kosdaq_close, kosdaq_change, _ = get_snapshot("^KQ11")

        if kospi_close is None or kosdaq_close is None:
            return {}

        return {
            "KOSPI": (kospi_close, kospi_change),
            "KOSDAQ": (kosdaq_close, kosdaq_change)
        }

    except:
        return {}


# ---------------- UI ----------------

st.title("🌅 이유나 PB 모닝브리프")

st.divider()

cols = st.columns(3)
market_data = {}

for i, (name, ticker) in enumerate(TICKERS.items()):
    close, change, pct = get_snapshot(ticker)

    market_data[name] = {
        "close": close,
        "change": change,
        "pct": pct
    }

    if close is None:
        cols[i % 3].metric(label=name, value="N/A")
    else:
        cols[i % 3].metric(
            label=name,
            value=f"{close:,.2f}",
            delta=f"{change:,.2f} ({pct:.2f}%)"
        )

st.divider()
st.subheader("KR 한국 시장")

k_cols = st.columns(2)
k_data = get_korea_market()

if not k_data:
    st.warning("한국 시장 데이터를 불러오지 못했습니다.")

for i, (name, (close, change)) in enumerate(k_data.items()):
    k_cols[i % 2].metric(
        label=name,
        value=f"{close:,.2f}",
        delta=f"{change:,.2f}"
    )

st.divider()

st.subheader("📝 아침 시황 코멘트")

summary = ""

kr_summary = ""
kospi_change = market_data.get("KOSPI", (None, None))[1]
kosdaq_change = market_data.get("KOSDAQ", (None, None))[1]
# KOSPI
if kospi_change is not None:
    if kospi_change > 10:
        kr_summary += "코스피 강세"
    elif kospi_change < -10:
        kr_summary += "코스피 약세"
    else:
        kr_summary += "코스피 보합"

# KOSDAQ
if kosdaq_change is not None:
    if kosdaq_change > 5:
        kr_summary += ", 코스닥 강세"
    elif kosdaq_change < -5:
        kr_summary += ", 코스닥 약세"
    else:
        kr_summary += ", 코스닥 보합"

nasdaq_pct = market_data.get("Nasdaq", {}).get("pct")
dxy_pct = market_data.get("달러인덱스", {}).get("pct")

# 나스닥
if nasdaq_pct is not None:
    if nasdaq_pct > 1:
        summary += "기술주 강세"
    elif nasdaq_pct < -1:
        summary += "기술주 약세"
    else:
        summary += "보합 흐름"

# 달러
if dxy_pct is not None:
    if dxy_pct > 0:
        summary += ", 달러 강세 동반"
    else:
        summary += ", 달러 약세"

# 종합 해석
if nasdaq_pct is not None and dxy_pct is not None:
    if nasdaq_pct > 1 and dxy_pct > 0:
        summary += " (금리/달러 부담에도 주식 강세)"
    elif nasdaq_pct < -1 and dxy_pct > 0:
        summary += " (달러 강세가 성장주 부담 요인)"
    elif -1 <= nasdaq_pct <= 1 and dxy_pct > 0:
        summary += " (달러 강세 속 방향성 탐색 구간)"
    elif -1 <= nasdaq_pct <= 1 and dxy_pct <= 0:
        summary += " (관망세 속 위험자산 심리 회복 여부 확인)"
    else:
        summary += " (위험자산 선호 흐름)"

if summary:
    st.info(f"📌 글로벌: {summary}")

if kr_summary:
    st.info(f"🇰🇷 한국: {kr_summary}")

st.subheader("🌍 미국 시장맵")
st.components.v1.html("""
<div class="tradingview-widget-container">
  <div id="tradingview_heatmap"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js">
  {
    "exchanges": [],
    "dataSource": "SPX500",
    "grouping": "sector",
    "blockSize": "market_cap_basic",
    "blockColor": "change",
    "locale": "kr",
    "symbolUrl": "",
    "colorTheme": "dark",
    "hasTopBar": false,
    "isDataSetEnabled": false,
    "isZoomEnabled": true,
    "hasSymbolTooltip": true,
    "width": "100%",
    "height": "500"
  }
  </script>
</div>
""", height=520)

st.subheader("🇰🇷 한국 섹터 미니맵")

korea_sectors = {
    "반도체": {
        "삼성전자": "005930.KS",
        "SK하이닉스": "000660.KS",
        "한미반도체": "042700.KS",
    },
    "2차전지": {
        "LG에너지솔루션": "373220.KS",
        "삼성SDI": "006400.KS",
        "에코프로비엠": "247540.KQ",
    },
    "자동차": {
        "현대차": "005380.KS",
        "기아": "000270.KS",
        "현대모비스": "012330.KS",
    },
    "금융": {
        "KB금융": "105560.KS",
        "신한지주": "055550.KS",
        "하나금융지주": "086790.KS",
    },
    "인터넷/게임": {
        "NAVER": "035420.KS",
        "카카오": "035720.KS",
        "크래프톤": "259960.KS",
    },
    "바이오": {
        "삼성바이오로직스": "207940.KS",
        "셀트리온": "068270.KS",
        "유한양행": "000100.KS",
    },
    "조선/방산": {
        "HD현대중공업": "329180.KS",
        "한화오션": "042660.KS",
        "한화에어로스페이스": "012450.KS",
    },
    "화장품/소비재": {
        "아모레퍼시픽": "090430.KS",
        "LG생활건강": "051900.KS",
        "코스맥스": "192820.KS",
    },
}

@st.cache_data(ttl=1800)
def get_stock_pct(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if hist.empty or len(hist) < 2:
            return None, None

        close = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2])
        pct = ((close - prev) / prev) * 100

        return close, pct
    except:
        return None, None


for sector, stocks in korea_sectors.items():
    st.markdown(f"### {sector}")
    cols = st.columns(3)

    for i, (name, ticker) in enumerate(stocks.items()):
        close, pct = get_stock_pct(ticker)

        if close is None:
            cols[i % 3].metric(name, "N/A")
        else:
            cols[i % 3].metric(
                label=name,
                value=f"{close:,.0f}",
                delta=f"{pct:.2f}%"
            )

st.subheader("📅 이번 주 주요 일정")
st.components.v1.iframe(
    "https://sslecal2.investing.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&importance=2,3&features=datepicker,timezone,timeselector,filters&countries=5&calType=week&timeZone=54&lang=18",
    height=520
)

st.caption("※ 본 자료는 시장지표 확인을 위한 참고자료이며, 특정 금융상품의 투자 권유나 매매 추천이 아닙니다.")
