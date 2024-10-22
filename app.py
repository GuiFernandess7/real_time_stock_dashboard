import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta
import time
import re
import ta

def fetch_stock_data(ticker, period, interval):
    end_date = datetime.now()
    if period == '1wk':
        start_date = end_date - timedelta(days=7)
        data = yf.download(ticker, start_date, end_date, interval=interval)
    else:
        data = yf.download(ticker, period=period, interval=interval)
    return data

def process_data(data):
    if data.index.tzinfo is None:
        data.index = data.index.tz_localize('UTC')
    data.index = data.index.tz_convert('US/Eastern')
    data.reset_index(inplace=True)
    data.rename(columns={'Date': 'Datetime'}, inplace=True)
    return data

def calculate_metrics(data):
    last_close = data['Close'].iloc[-1]
    prev_close = data['Close'].iloc[-2]
    change = last_close - prev_close
    pct_change = (change / prev_close) * 100
    high = data['High'].max()
    low = data['Low'].min()
    volume = data['Volume'].sum()
    return last_close, change, pct_change, high, low, volume

def add_technical_indicators(data):
    data['SMA_20'] = ta.trend.sma_indicator(data['Close'], window=20)
    data['EMA_20'] = ta.trend.ema_indicator(data['Close'], window=20)
    return data

st.set_page_config(layout="wide")
st.title('Real Time Stock Dashboard')

if 'data' not in st.session_state:
    st.session_state.data = {}
if 'data_today' not in st.session_state:
    st.session_state.data_today = {}

st.sidebar.header('Chart Parameters')
ticker = st.sidebar.text_input('Ticker', 'ADBE')
time_period = st.sidebar.selectbox('Time Period', ['1d', '1wk', '1mo', '1y', 'max'])
chart_type = st.sidebar.selectbox('Chart Type', ['Candlestick', 'Line'])
indicators = st.sidebar.multiselect('Technical Indicators', ['SMA 20', 'EMA 20'])

interval_mapping = {
    '1d': '1m',
    '1wk': '30m',
    '1mo': '1d',
    '1y': '1wk',
    'max': '1wk'
}

currency = 'BRL' if re.search(r'\.SA$', ticker) else 'USD'

if st.sidebar.button('Update'):
    st.session_state.data = fetch_stock_data(ticker, time_period, interval_mapping[time_period])
    st.session_state.data = process_data(st.session_state.data)
    st.session_state.data = add_technical_indicators(st.session_state.data)

if 'date_of_sell_or_buy' not in st.session_state:
    st.session_state.date_of_sell_or_buy = datetime.today()

if 'registrar_mensagem' not in st.session_state:
    st.session_state.registrar_mensagem = None

with st.sidebar.expander("Register Sale or Purchase"):
    type = st.selectbox("Type", ["Purchase", "Sale"])

    current_value = st.session_state.data["Close"][0] if 'Close' in st.session_state.data and len(st.session_state.data["Close"]) > 0 else 0
    st.write(f"Valor Atual: R$ {current_value:.2f}")

    if st.button("Registrar"):
        st.session_state.registrar_mensagem = f"{type} registered successfully! Date: {datetime.today()}, Current value: R$ {current_value:.2f}"

        message_placeholder = st.empty()
        message_placeholder.success(st.session_state.registrar_mensagem)
        time.sleep(1)
        message_placeholder.empty()

if 'Close' in st.session_state.data and len(st.session_state.data["Close"]) > 0:
    last_close, change, pct_change, high, low, volume = calculate_metrics(st.session_state.data)

    st.metric(label=f"{ticker} Last Price", value=f"{last_close:.2f} {currency}", delta=f"{change:.2f} ({pct_change:.2f}%)")

    col1, col2, col3 = st.columns(3)
    col1.metric("High", f"{high:.2f} {currency}")
    col2.metric("Low", f"{low:.2f} {currency}")
    col3.metric("Volume", f"{volume:,}")

    fig = go.Figure()
    if chart_type == 'Candlestick':
        fig.add_trace(go.Candlestick(x=st.session_state.data['Datetime'],
                                     open=st.session_state.data['Open'],
                                     high=st.session_state.data['High'],
                                     low=st.session_state.data['Low'],
                                     close=st.session_state.data['Close']))
    else:
        fig = px.line(st.session_state.data, x='Datetime', y='Close')

    for indicator in indicators:
        if indicator == 'SMA 20':
            fig.add_trace(go.Scatter(x=st.session_state.data['Datetime'], y=st.session_state.data['SMA_20'], name='SMA 20'))
        elif indicator == 'EMA 20':
            fig.add_trace(go.Scatter(x=st.session_state.data['Datetime'], y=st.session_state.data['EMA_20'], name='EMA 20'))

    fig.update_layout(title=f'{ticker} {time_period.upper()} Chart',
                    xaxis_title='Time',
                    yaxis_title='Price (USD)',
                    height=600)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader('Historical Data')
    st.dataframe(st.session_state.data[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']])

    st.subheader('Technical Indicators')
    st.dataframe(st.session_state.data[['Datetime', 'SMA_20', 'EMA_20']])

    st.sidebar.header('Real-Time Stock Prices')
    stock_symbols = ['AAPL', 'GOOGL', 'AMZN', 'MSFT']
    for symbol in stock_symbols:
        real_time_data = fetch_stock_data(symbol, '1d', '1m')
        if not real_time_data.empty:
            real_time_data = process_data(real_time_data)
            last_price = real_time_data['Close'].iloc[-1]
            change = last_price - real_time_data['Open'].iloc[0]
            pct_change = (change / real_time_data['Open'].iloc[0]) * 100
            st.sidebar.metric(f"{symbol}", f"{last_price:.2f} USD", f"{change:.2f} ({pct_change:.2f}%)")

st.sidebar.subheader('About')
st.sidebar.info('This dashboard provides stock data and technical indicators for various time periods. Use the sidebar to configure the settings.')