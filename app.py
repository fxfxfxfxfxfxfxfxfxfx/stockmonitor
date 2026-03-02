import streamlit as st
import pandas as pd
import numpy as np
import time

# 테스트용 상위 종목 데이터
TEST_STOCKS = [
    {'code': '005930', 'name': '삼성전자', 'price': 80000, 'market_cap': 500000},
    {'code': '000660', 'name': 'SK하이닉스', 'price': 130000, 'market_cap': 90000},
    {'code': '035420', 'name': 'NAVER', 'price': 210000, 'market_cap': 35000},
    {'code': '035720', 'name': '카카오', 'price': 65000, 'market_cap': 28000},
    {'code': '000270', 'name': '기아', 'price': 120000, 'market_cap': 32000},
    {'code': '005380', 'name': '현대차', 'price': 250000, 'market_cap': 45000},
    {'code': '003670', 'name': '포스코홀딩스', 'price': 380000, 'market_cap': 28000},
]

def calculate_rsi(prices, period=14):
    """RSI(14) 계산"""
    if len(prices) < period + 1:
        return None
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_rsi_ma(rsi_values, ma_period=9):
    """RSI(14)에 9일 이동평균 적용"""
    if rsi_values is None or len(rsi_values) < ma_period:
        return None
    return np.mean(rsi_values[-ma_period:])

def calculate_sentiment(prices, period=12):
    """투자심리도 = 최근 N일 중 상승일 비율 * 100"""
    if len(prices) < period:
        return None
    
    changes = np.diff(prices[-period:])
    up_days = np.sum(changes > 0)
    sentiment = (up_days / period) * 100
    return sentiment

def simulate_stock_data(code, days=30):
    """각 종목별 가상 주가 데이터 생성"""
    np.random.seed(int(code) % 1000)
    base_price = TEST_STOCKS[int(code[:2]) % len(TEST_STOCKS)]['price']
    prices = []
    current = base_price
    
    for _ in range(days):
        change = np.random.normal(0, 0.02)  # 2% 변동성
        current *= (1 + change)
        prices.append(current)
    
    return np.array(prices)

def main():
    st.set_page_config(page_title="주식필터링", page_icon="📈", layout="wide")
    st.title("📊 한국 주식시장 종목 필터링 (RSI + 투자심리도)")

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🔄 상장 종목 목록 로딩", use_container_width=True):
            st.session_state.stock_data = TEST_STOCKS.copy()
            st.success(f"✅ 로드 완료: {len(st.session_state.stock_data)}개 종목")

    if "stock_data" not in st.session_state or not st.session_state.stock_data:
        st.warning("상장 종목 목록을 먼저 로딩하세요.")
        st.stop()

    stock_data = st.session_state.stock_data
    st.info(f"📋 총 {len(stock_data)}개 종목 로딩됨")

    st.subheader("🔧 필터 조건")
    
    col1, col2 = st.columns(2)
    with col1:
        use_market_cap = st.checkbox("시가총액 필터 사용", value=True)
        market_cap_value = st.number_input("시가총액 기준 (억)", value=30000.0, step=5000.0)
        market_cap_op = st.selectbox("시가총액 조건", ["이상", "이하"])
    
    with col2:
        use_volume_surge = st.checkbox("거래량 증가율 필터 사용")
        volume_surge_value = st.number_input("거래량 증가율 기준 (%)", value=200.0, step=50.0)
        volume_surge_op = st.selectbox("거래량 조건", ["이상", "이하"])

    col3, col4 = st.columns(2)
    with col3:
        use_low_days = st.checkbox("n일 신저가 필터 사용")
        low_days_value = st.number_input("n일", value=20, step=5)
    
    # 🔥 RSI 필터 추가
    use_rsi = st.checkbox("🔥 RSI(14,9) 필터 사용")
    if use_rsi:
        col5, col6, col7 = st.columns(3)
        with col5:
            rsi_min = st.number_input("RSI 최소값", value=20.0, min_value=0.0, max_value=50.0, step=5.0)
        with col6:
            rsi_max = st.number_input("RSI 최대값", value=80.0, min_value=50.0, max_value=100.0, step=5.0)
        with col7:
            st.info("💡 과매도: 30이하, 과매수: 70이상")
    
    # 💭 투자심리도 필터 추가
    use_sentiment = st.checkbox("💭 투자심리도 필터 사용")
    if use_sentiment:
        col8, col9 = st.columns(2)
        with col8:
            sentiment_min = st.number_input("투자심리도 최소 (%)", value=0.0, max_value=50.0, step=10.0)
        with col9:
            sentiment_max = st.number_input("투자심리도 최대 (%)", value=100.0, min_value=50.0, max_value=100.0, step=10.0)
        st.caption("💡 낮을수록 공포, 높을수록 탐욕")

    if st.button("🚀 필터링 실행", use_container_width=True):
        results = []
        progress = st.progress(0)
        total = len(stock_data)

        for i, stock in enumerate(stock_data):
            progress.progress((i + 1) / total)
            passed = True
            
            # 시가총액 필터
            if use_market_cap:
                if market_cap_op == "이상" and stock['market_cap'] < market_cap_value:
                    passed = False
                elif market_cap_op == "이하" and stock['market_cap'] > market_cap_value:
                    passed = False
            
            # 거래량 필터 (시뮬레이션)
            volume_surge = None
            if use_volume_surge and passed:
                volume_surge = np.random.uniform(50, 500)
                if volume_surge_op == "이상" and volume_surge < volume_surge_value:
                    passed = False
                elif volume_surge_op == "이하" and volume_surge > volume_surge_value:
                    passed = False
            
            # 신저가 필터 (시뮬레이션)
            low_days, is_low = None, False
            if use_low_days and passed:
                prices = simulate_stock_data(stock['code'], int(low_days_value))
                recent_prices = prices[-int(low_days_value):]
                low_days = np.min(recent_prices)
                is_low = (recent_prices[-1] == low_days)
                if not is_low:
                    passed = False
            
            # 🔥 RSI 필터
            rsi_14_9 = None
            if use_rsi and passed:
                prices = simulate_stock_data(stock['code'], 30)
                rsi_14 = calculate_rsi(prices, 14)
                rsi_14_9 = calculate_rsi_ma([rsi_14], 9) or rsi_14  # 9일MA는 단일값이므로 RSI(14) 그대로
                if not (rsi_min <= rsi_14_9 <= rsi_max):
                    passed = False
            
            # 💭 투자심리도 필터
            sentiment = None
            if use_sentiment and passed:
                prices = simulate_stock_data(stock['code'], 20)
                sentiment = calculate_sentiment(prices, 12)
                if not (sentiment_min <= sentiment <= sentiment_max):
                    passed = False

            if passed:
                code6 = str(stock['code']).zfill(6)
                naver_url = f"https://finance.naver.com/item/fchart.naver?code={code6}"
                results.append({
                    "종목코드": code6,
                    "종목명": stock['name'],
                    "현재가": f"{stock['price']:,.0f}",
                    "시가총액(억)": f"{stock['market_cap']:,.0f}",
                    "n일신저가": f"{low_days:,.0f}" if low_days else "N/A",
                    "신저가": "O" if is_low else "X",
                    "거래량증가율(%)": f"{volume_surge:.1f}%" if volume_surge else "N/A",
                    f"RSI(14,9)": f"{rsi_14_9:.1f}" if rsi_14_9 else "N/A",
                    "투자심리도": f"{sentiment:.1f}%" if sentiment else "N/A",
                    "네이버차트": naver_url,
                })

        st.success(f"✅ 완료: {len(results)}개 종목 필터링됨")
        
        if results:
            df = pd.DataFrame(results)
            st.subheader("📋 필터링 결과")
            st.dataframe(df, use_container_width=True)
            
            st.subheader("📈 네이버 차트")
            df_link = df[['종목코드', '종목명', 'RSI(14,9)', '투자심리도', '네이버차트']].copy()
            df_link["네이버차트"] = df_link["네이버차트"].apply(
                lambda x: f'<a href="{x}" target="_blank" style="color:#1f77b4;font-weight:bold;">🔗 차트 열기</a>'
            )
            st.markdown(df_link.to_html(escape=False, index=False), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
