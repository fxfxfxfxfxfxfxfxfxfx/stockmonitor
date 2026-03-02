import streamlit as st
import pandas as pd
import numpy as np
import time

# 테스트용 상위 종목 데이터 (실제 크롤링 대신)
TEST_STOCKS = [
    {'code': '005930', 'name': '삼성전자', 'price': 80000, 'market_cap': 500000},
    {'code': '000660', 'name': 'SK하이닉스', 'price': 130000, 'market_cap': 90000},
    {'code': '035420', 'name': 'NAVER', 'price': 210000, 'market_cap': 35000},
    {'code': '035720', 'name': '카카오', 'price': 65000, 'market_cap': 28000},
    {'code': '000270', 'name': '기아', 'price': 120000, 'market_cap': 32000},
]

def simulate_volume_surge():
    return np.random.uniform(50, 500)

def simulate_days_low(days=20):
    prices = np.random.normal(100000, 20000, days)
    current = prices[-1]
    low = np.min(prices)
    return low, (current == low)

def main():
    st.set_page_config(page_title="주식필터링", page_icon="📈", layout="wide")
    st.title("📊 한국 주식시장 종목 필터링")

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

    use_low_days = st.checkbox("n일 신저가 필터 사용")
    low_days_value = st.number_input("n일", value=20, step=5)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 필터링 실행", use_container_width=True):
            results = []
            progress = st.progress(0)
            total = len(stock_data)

            for i, stock in enumerate(stock_data):
                progress.progress((i + 1) / total)
                passed = True
                volume_surge = None
                low_days, is_low = None, False

                if use_market_cap:
                    if market_cap_op == "이상" and stock['market_cap'] < market_cap_value:
                        passed = False
                    elif market_cap_op == "이하" and stock['market_cap'] > market_cap_value:
                        passed = False

                if use_volume_surge and passed:
                    volume_surge = simulate_volume_surge()
                    if volume_surge_op == "이상" and volume_surge < volume_surge_value:
                        passed = False
                    elif volume_surge_op == "이하" and volume_surge > volume_surge_value:
                        passed = False

                if use_low_days and passed:
                    low_days, is_low = simulate_days_low(int(low_days_value))
                    if not is_low:
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
                        "네이버차트": naver_url,
                    })

            st.success(f"✅ 완료: {len(results)}개 종목")
            
            if results:
                df = pd.DataFrame(results)
                st.subheader("📋 필터링 결과")
                st.dataframe(df, use_container_width=True)
                
                st.subheader("📈 네이버 차트")
                df_link = df[['종목코드', '종목명', '네이버차트']].copy()
                df_link["네이버차트"] = df_link["네이버차트"].apply(
                    lambda x: f'<a href="{x}" target="_blank" style="color:#1f77b4;font-weight:bold;">🔗 차트 열기</a>'
                )
                st.markdown(df_link.to_html(escape=False, index=False), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
