import os
import requests
import pandas as pd
import numpy as np
import streamlit as st
import re

@st.cache_data
def load_stock_list():
    stock_list = []
    page = 1
    headers = {'User-Agent': 'Mozilla/5.0'}

    while True:
        url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok=0&page={page}"
        html = requests.get(url, headers=headers).text
        dfs = pd.read_html(html)

        if dfs is None or len(dfs) < 2:
            break

        df = dfs[1].dropna(subset=['종목명'])
        if df.empty:
            break

        df['시가총액(억)'] = df['시가총액'].astype(str).str.replace(',', '').astype(float)
        
        # 코드 추출 (BeautifulSoup 없이 정규식으로)
        code_map = {}
        code_pattern = r'href="([^"]*code=(\d+)[^"]*)"[^>]*>([^<]+)<'
        matches = re.findall(code_pattern, html)
        for url, code, name in matches:
            code_map[name.strip()] = code

        for _, row in df.iterrows():
            if row['시가총액(억)'] >= 10000 and row['종목명'] in code_map:
                stock_list.append({
                    'symbol': f"{code_map[row['종목명']]}.KS",
                    'code': code_map[row['종목명']],
                    'name': row['종목명'],
                    'price': row['현재가'] if '현재가' in row else 0,
                    'market_cap': row['시가총액(억)'],
                })

        page += 1
        if page > 10:  # 무한루프 방지
            break

    return stock_list

def get_naver_daily_volumes(code, days=6):
    volumes = []
    page = 1
    headers = {'User-Agent': 'Mozilla/5.0'}
    while len(volumes) < days:
        url = f"https://finance.naver.com/item/sise_day.naver?code={code}&page={page}"
        res = requests.get(url, headers=headers)
        dfs = pd.read_html(res.text)

        if dfs is None or len(dfs) == 0:
            break

        df = dfs[0].dropna(subset=['거래량'])
        volumes += df['거래량'].astype(str).str.replace(',', '').astype(float).tolist()
        page += 1
        if page > 2:
            break

    return volumes[:days][::-1]

def get_naver_days_low(code, days=20):
    prices = []
    page = 1
    headers = {'User-Agent': 'Mozilla/5.0'}
    while len(prices) < days:
        url = f"https://finance.naver.com/item/sise_day.naver?code={code}&page={page}"
        res = requests.get(url, headers=headers)
        dfs = pd.read_html(res.text)
        if dfs is None or len(dfs) == 0:
            break
        df = dfs[0].dropna(subset=['종가'])
        prices += df['종가'].astype(str).str.replace(',', '').astype(float).tolist()
        page += 1
        if page > 10:
            break

    prices = prices[::-1]
    if not prices or len(prices) < days:
        return None, False

    recent_prices = prices[-days:]
    current_price = recent_prices[-1]
    days_low = min(recent_prices)
    is_low = (current_price == days_low)
    return days_low, is_low

def main():
    st.set_page_config(page_title="주식필터링", page_icon="📈", layout="wide")
    st.title("📊 한국 주식시장 종목 필터링")

    if "stock_data" not in st.session_state:
        st.session_state.stock_data = None

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🔄 상장 종목 목록 로딩", use_container_width=True):
            with st.spinner("종목 목록 로딩 중..."):
                st.session_state.stock_data = load_stock_list()
            st.success(f"✅ 로드 완료: {len(st.session_state.stock_data)}개 종목")

    stock_data = st.session_state.stock_data

    if stock_data:
        st.info(f"📋 총 {len(stock_data)}개 종목 로딩됨")

    st.subheader("🔧 필터 조건")
    
    col1, col2 = st.columns(2)
    with col1:
        use_market_cap = st.checkbox("시가총액 필터 사용", value=True)
        market_cap_value = st.number_input("시가총액 기준 (억)", value=10000.0, step=1000.0)
        market_cap_op = st.selectbox("시가총액 조건", ["이상", "이하"])
    
    with col2:
        use_volume_surge = st.checkbox("거래량 증가율 필터 사용")
        volume_surge_value = st.number_input("거래량 증가율 기준 (%)", value=200.0, step=50.0)
        volume_surge_op = st.selectbox("거래량 조건", ["이상", "이하"])

    col3, col4 = st.columns(2)
    with col3:
        use_low_days = st.checkbox("n일 신저가 필터 사용")
        low_days_value = st.number_input("n일 (최근 n일 기준)", value=20, step=5)

    if st.button("🚀 필터링 실행", use_container_width=True):
        if not stock_data:
            st.warning("❌ 먼저 상장 종목 목록을 로딩하세요.")
        else:
            results = []
            progress = st.progress(0)
            total = len(stock_data)
            st.info("필터링 진행 중...")

            for i, stock in enumerate(stock_data):
                progress.progress((i + 1) / total)
                passed = True
                volume_surge = None
                low_days, is_low = None, False

                if use_market_cap:
                    if market_cap_op == "이상":
                        if stock['market_cap'] < market_cap_value:
                            passed = False
                    else:
                        if stock['market_cap'] > market_cap_value:
                            passed = False

                if use_volume_surge and passed:
                    try:
                        vols = get_naver_daily_volumes(stock['code'], days=6)
                        if vols and len(vols) >= 6 and vols[0] > 0:
                            avg_vol = np.mean(vols[1:6])
                            if avg_vol > 0:
                                volume_surge = (vols[0] / avg_vol) * 100

                        if volume_surge is None:
                            passed = False
                        elif volume_surge_op == "이상":
                            if volume_surge < volume_surge_value:
                                passed = False
                        else:
                            if volume_surge > volume_surge_value:
                                passed = False
                    except:
                        passed = False

                if use_low_days and passed:
                    try:
                        low_days, is_low = get_naver_days_low(stock['code'], days=int(low_days_value))
                        if not is_low:
                            passed = False
                    except:
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
                        "n일신저가여부": "O" if is_low else "X",
                        "거래량증가율(%)": f"{volume_surge:.1f}" if volume_surge else "N/A",
                        "네이버차트": naver_url,
                    })

            st.success(f"✅ 완료: {len(results)}개 종목 필터링됨")
            
            if results:
                df = pd.DataFrame(results)
                
                st.subheader("📋 필터링 결과")
                st.dataframe(df, use_container_width=True)
                
                st.subheader("📈 네이버 차트 바로가기")
                df_link = df.copy()
                df_link["네이버차트"] = df_link["네이버차트"].apply(
                    lambda url: f'<a href="{url}" target="_blank" style="color:blue; font-weight:bold;">🔗 차트</a>'
                )
                st.markdown(df_link[['종목코드', '종목명', '현재가', '네이버차트']].to_html(escape=False, index=False), unsafe_allow_html=True)
                
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="💾 CSV 다운로드",
                    data=csv,
                    file_name=f"주식필터_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("⚠️ 조건에 맞는 종목이 없습니다.")

if __name__ == "__main__":
    main()

