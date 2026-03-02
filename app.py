import os
import requests
import pandas as pd
import numpy as np
import streamlit as st
import re
import time

@st.cache_data(ttl=3600)  # 1시간 캐시
def load_stock_list():
    stock_list = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # 코스피 상위 100개만 미리 가져오기 (lxml 문제 우회)
    for page in range(1, 11):
        try:
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok=0&page={page}"
            time.sleep(0.5)  # 서버 부하 방지
            html = requests.get(url, headers=headers, timeout=10).text
            
            # 간단한 문자열 파싱으로 종목코드 추출
            code_pattern = r'href="/item/main.naver\?code=(\d{6})"[^>]*>([^<]+)<'
            matches = re.findall(code_pattern, html)
            
            # pandas read_html 대신 수동 파싱
            table_pattern = r'<tr[^>]*>\s*<td[^>]*>\s*(\d{6})\s*</td[^>]*>\s*<td[^>]*>\s*([^<]+)\s*</td[^>]*>\s*<td[^>]*>\s*([\d,]+)\s*</td[^>]*>'
            table_matches = re.findall(table_pattern, html)
            
            for code, name, market_cap_str in table_matches:
                try:
                    market_cap = float(market_cap_str.replace(',', ''))
                    if market_cap >= 10000:
                        stock_list.append({
                            'symbol': f"{code}.KS",
                            'code': code,
                            'name': name.strip(),
                            'price': 0,
                            'market_cap': market_cap
                        })
                except:
                    continue
                    
            if len(stock_list) >= 200:  # 충분히 모이면 중단
                break
                
        except Exception as e:
            st.error(f"페이지 {page} 로딩 실패: {e}")
            continue
    
    return stock_list[:200]

def get_naver_daily_volumes(code, days=6):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        volumes = []
        url = f"https://finance.naver.com/item/sise_day.naver?code={code}"
        html = requests.get(url, headers=headers, timeout=10).text
        dfs = pd.read_html(html)
        
        if dfs and len(dfs) > 0:
            df = dfs[0].dropna(subset=['거래량'])
            volumes = df['거래량'].astype(str).str.replace(',', '').astype(float).tolist()
        
        return volumes[:days][::-1]
    except:
        return None

def get_naver_days_low(code, days=20):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        prices = []
        url = f"https://finance.naver.com/item/sise_day.naver?code={code}"
        html = requests.get(url, headers=headers, timeout=10).text
        dfs = pd.read_html(html)
        
        if dfs and len(dfs) > 0:
            df = dfs[0].dropna(subset=['종가'])
            prices = df['종가'].astype(str).str.replace(',', '').astype(float).tolist()
        
        prices = prices[::-1][:days]
        if len(prices) >= days:
            current_price = prices[-1]
            days_low = min(prices)
            return days_low, (current_price == days_low)
        return None, False
    except:
        return None, False

def main():
    st.set_page_config(page_title="주식필터링", page_icon="📈", layout="wide")
    st.title("📊 한국 주식시장 종목 필터링")

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🔄 상장 종목 목록 로딩", use_container_width=True):
            with st.spinner("종목 목록 로딩 중..."):
                st.session_state.stock_data = load_stock_list()
            if st.session_state.stock_data:
                st.success(f"✅ 로드 완료: {len(st.session_state.stock_data)}개 종목")
            else:
                st.error("❌ 종목 로딩 실패")

    if "stock_data" not in st.session_state or not st.session_state.stock_data:
        st.warning("상장 종목 목록을 먼저 로딩하세요.")
        st.stop()

    stock_data = st.session_state.stock_data
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

    use_low_days = st.checkbox("n일 신저가 필터 사용")
    low_days_value = st.number_input("n일 (최근 n일 기준)", value=20, step=5)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 필터링 실행", use_container_width=True):
            results = []
            progress = st.progress(0)
            total = min(100, len(stock_data))  # 처음 100개만
            st.info(f"필터링 진행 중... ({total}개 종목)")

            for i, stock in enumerate(stock_data[:total]):
                progress.progress((i + 1) / total)
                passed = True
                volume_surge = None
                low_days, is_low = None, False

                # 시가총액 필터
                if use_market_cap:
                    if market_cap_op == "이상" and stock['market_cap'] < market_cap_value:
                        passed = False
                    elif market_cap_op == "이하" and stock['market_cap'] > market_cap_value:
                        passed = False

                # 거래량 필터
                if use_volume_surge and passed:
                    vols = get_naver_daily_volumes(stock['code'])
                    if vols and len(vols) >= 6 and vols[0] > 0:
                        avg_vol = np.mean(vols[1:6])
                        if avg_vol > 0:
                            volume_surge = (vols[0] / avg_vol) * 100
                    
                    if volume_surge is None:
                        passed = False
                    elif volume_surge_op == "이상" and volume_surge < volume_surge_value:
                        passed = False
                    elif volume_surge_op == "이하" and volume_surge > volume_surge_value:
                        passed = False

                # 신저가 필터
                if use_low_days and passed:
                    low_days, is_low = get_naver_days_low(stock['code'], int(low_days_value))
                    if not is_low:
                        passed = False

                if passed:
                    code6 = str(stock['code']).zfill(6)
                    naver_url = f"https://finance.naver.com/item/fchart.naver?code={code6}"
                    results.append({
                        "종목코드": code6,
                        "종목명": stock['name'][:12],
                        "현재가": f"{stock['price']:,.0f}" if stock['price'] else "N/A",
                        "시가총액(억)": f"{stock['market_cap']:,.0f}",
                        "n일신저가": f"{low_days:,.0f}" if low_days else "N/A",
                        "신저가": "O" if is_low else "X",
                        "거래량증가율(%)": f"{volume_surge:.1f}%" if volume_surge else "N/A",
                        "네이버차트": naver_url,
                    })

            st.success(f"✅ 완료: {len(results)}개 종목 필터링됨")
            
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
                
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="💾 CSV 다운로드",
                    data=csv,
                    file_name=f"주식필터_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    main()
