import streamlit as st
import pandas as pd
import numpy as np
import requests
import re
import time

@st.cache_data(ttl=3600)
def load_stock_list():
    stock_list = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for page in range(1, 41):  # 코스피 전체 400개
        try:
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok=0&page={page}"
            response = requests.get(url, headers=headers, timeout=10)
            html = response.text
            
            # 종목코드 추출
            code_matches = re.findall(r'code=(\d{6})" class="tltle"[^>]*>([^<]+)<', html)
            # 테이블 파싱
            table_data = pd.read_html(html)
            if len(table_data) > 1:
                df = table_data[1]
                df['시가총액(억)'] = df['시가총액'].str.replace(',', '').astype(float)
                
                for idx, row in df.iterrows():
                    name = row['종목명']
                    if name in dict(code_matches) and row['시가총액(억)'] >= 10000:
                        code = dict(code_matches)[name]
                        stock_list.append({
                            'code': code,
                            'name': name,
                            'price': row.get('현재가', 0),
                            'market_cap': row['시가총액(억)']
                        })
            time.sleep(0.3)
        except:
            continue
    
    return stock_list

def get_stock_data(code):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = f"https://finance.naver.com/item/sise_day.naver?code={code}"
        html = requests.get(url, headers=headers, timeout=10).text
        dfs = pd.read_html(html)
        if dfs:
            df = dfs[0].dropna(subset=['종가'])
            prices = df['종가'].str.replace(',', '').astype(float).tolist()[-30:]
            return prices[::-1]  # 최근순
    except:
        pass
    return None

def calculate_rsi(prices, period=14):
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
    return 100 - (100 / (1 + rs))

def calculate_sentiment(prices, period=12):
    if len(prices) < period:
        return None
    changes = np.diff(prices[-period:])
    up_days = np.sum(changes > 0)
    return (up_days / period) * 100

def main():
    st.set_page_config(page_title="주식필터링", page_icon="📈", layout="wide")
    st.title("📊 한국 주식 필터링 (전체 종목)")

    if st.button("🔄 전체 종목 로딩"):
        with st.spinner("로딩중..."):
            st.session_state.stock_data = load_stock_list()
        st.success(f"✅ {len(st.session_state.stock_data)}개 종목 로딩")

    if "stock_data" not in st.session_state:
        st.warning("로딩 버튼 클릭")
        st.stop()

    # 필터들
    col1, col2 = st.columns(2)
    with col1:
        market_cap = st.number_input("시총(억)", 10000)
        rsi_low, rsi_high = st.slider("RSI", 0, 100, (20, 80))
        sentiment_low = st.slider("투자심리도(%)", 0, 100, (0, 50))
    
    if st.button("🚀 필터링"):
        results = []
        progress = st.progress(0)
        
        for i, stock in enumerate(st.session_state.stock_data[:200]):  # 상위 200개
            progress.progress((i+1)/200)
            prices = get_stock_data(stock['code'])
            
            if prices:
                rsi = calculate_rsi(prices)
                sentiment = calculate_sentiment(prices)
                
                if (stock['market_cap'] >= market_cap and 
                    rsi_low <= rsi <= rsi_high and 
                    sentiment_low <= sentiment <= 50):
                    
                    results.append({
                        '코드': stock['code'],
                        '종목명': stock['name'],
                        '시총': f"{stock['market_cap']:,.0f}",
                        'RSI': f"{rsi:.1f}",
                        '심리도': f"{sentiment:.1f}%",
                        '차트': f"https://finance.naver.com/item/fchart.naver?code={stock['code']}"
                    })
        
        df = pd.DataFrame(results)
        st.dataframe(df)
        
        df_chart = df.copy()
        df_chart['차트'] = df_chart['차트'].apply(
            lambda x: f'<a href="{x}" target="_blank">차트</a>'
        )
        st.markdown(df_chart.to_html(escape=False), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
