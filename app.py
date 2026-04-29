import requests
import re
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="yuna의 모닝브리프", layout="wide")

TICKERS = {
    "Nasdaq": "^IXIC",
    "S&P500": "^GSPC",
    "VIX": "^VIX",
    "미국채10Y": "^TNX",
    "달러인덱스": "DX-Y.NYB",
    "WTI": "CL=F",
    "Gold": "GC=F"
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

st.title("🌅 yuna의 모닝브리프")

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

comment = []

if market_data["Nasdaq"]["pct"] is not None:
    if market_data["Nasdaq"]["pct"] > 1:
        comment.append("나스닥 강세 흐름으로 기술주 투자심리가 양호합니다.")
    elif market_data["Nasdaq"]["pct"] < -1:
        comment.append("나스닥 약세로 성장주 변동성 확대에 유의할 필요가 있습니다.")
    else:
        comment.append("나스닥은 보합권에 가까운 흐름입니다.")

if market_data["VIX"]["close"] is not None:
    if market_data["VIX"]["close"] >= 20:
        comment.append("VIX가 높은 수준이라 시장 경계심이 남아 있습니다.")
    else:
        comment.append("VIX는 비교적 안정적인 수준입니다.")

if market_data["미국채10Y"]["close"] is not None:
    comment.append(f'미국채 10년물 금리는 {market_data["미국채10Y"]["close"]:.2f}% 수준입니다.')

if market_data["달러인덱스"]["pct"] is not None:
    if market_data["달러인덱스"]["pct"] > 0:
        comment.append("달러 강세 흐름이 이어지고 있습니다.")
    elif market_data["달러인덱스"]["pct"] < 0:
        comment.append("달러는 소폭 약세 흐름입니다.")

for line in comment:
    st.write(f"- {line}")

st.divider()

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

st.subheader("🇰🇷 한국 시장맵")
st.components.v1.html("""
<div class="tradingview-widget-container">
  <div id="tradingview_korea_heatmap"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js">
  {
    "exchanges": [],
    "dataSource": "KOSPI",
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

st.subheader("📅 이번 주 주요 일정")
st.components.v1.iframe(
    "https://sslecal2.investing.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&importance=2,3&features=datepicker,timezone,timeselector,filters&countries=5&calType=week&timeZone=54&lang=18",
    height=520
)

st.caption("※ 본 자료는 시장지표 확인을 위한 참고자료이며, 특정 금융상품의 투자 권유나 매매 추천이 아닙니다.")
