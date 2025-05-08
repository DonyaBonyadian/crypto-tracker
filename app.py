import streamlit as st
import requests
import pandas as pd
import altair as alt
import time
from datetime import datetime

# --- CONFIG ---
BASE_URL = "https://api.coingecko.com/api/v3"
st.set_page_config(page_title="Crypto Price Tracker", page_icon="💰", layout="wide")


# --- FUNCTIONS ---

@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_current_price(coin_id, currency):
    url = f"{BASE_URL}/simple/price"
    params = {"ids": coin_id, "vs_currencies": currency, "include_market_cap": "true", "include_24hr_change": "true"}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 429:
        st.warning("Rate limit exceeded. Please try again later.")
        return {}
    else:
        st.error(f"Error fetching current price: {response.status_code}")
        return {}


@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_historical_prices(coin_id, currency, days=7):
    url = f"{BASE_URL}/coins/{coin_id}/market_chart"
    params = {"vs_currency": currency, "days": days}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if "prices" in data:
            df = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
            df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df[["date", "price"]]
    elif response.status_code == 429:
        st.warning("Rate limit exceeded. Please try again later.")
    else:
        st.error(f"Error fetching historical data: {response.status_code}")
    return pd.DataFrame()


# --- SIDEBAR CONTROLS ---
st.sidebar.title("🔧 Settings")

coins = st.sidebar.multiselect("Choose coins to compare", ["bitcoin", "ethereum", "cardano", "dogecoin"],
                               default=["bitcoin"])
currency = st.sidebar.selectbox("Currency", ["usd", "eur", "cad", "gbp"], index=0)
days = st.sidebar.slider("Days of history", 1, 30, 7)

refresh_interval = st.sidebar.selectbox("Auto-refresh every (seconds)", [0, 10, 30, 60], index=0)
manual_refresh = st.sidebar.button("🔁 Refresh now")

# --- MAIN PAGE ---
st.title("💰 Crypto Price Tracker")
st.write("Track cryptocurrency prices and explore historical data")

# --- DISPLAY PRICE DATA ---
col1, col2 = st.columns(2)

# Left column: Current Price
with col1:
    st.subheader(f"Current {coins[0].title()} Price ({currency.upper()})")
    price_data = fetch_current_price(coins[0], currency)
    if price_data and coins[0] in price_data:
        current_price = price_data[coins[0]][currency]
        market_cap = price_data[coins[0]].get(f"{currency}_market_cap", "N/A")
        change_24h = price_data[coins[0]].get(f"{currency}_24h_change", "N/A")

        st.metric(label="Price", value=f"{current_price:,.2f}")
        st.markdown(f"**Market Cap**: {market_cap}")
        st.markdown(f"**24h Change**: {change_24h}%")

    else:
        st.warning("Unable to fetch current price.")

# Right column: Historical Chart
with col2:
    st.subheader(f"Historical Price - Last {days} Days")

    # Fetch and plot historical data for selected coins
    dfs = {}
    for coin in coins:
        df = fetch_historical_prices(coin, currency, days)
        if not df.empty:
            dfs[coin] = df

    if dfs:
        # Create an Altair chart for each coin
        combined_df = pd.concat(dfs.values(), keys=dfs.keys())
        combined_df.reset_index(level=0, inplace=True)
        combined_df.rename(columns={"level_0": "coin"}, inplace=True)

        chart = alt.Chart(combined_df).mark_line().encode(
            x="date:T",
            y="price:Q",
            color="coin:N",
            tooltip=["coin:N", "date:T", "price:Q"]
        ).properties(width=700, height=400)

        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("No historical price data available.")

# --- STATISTICAL SUMMARY ---
st.subheader("Statistical Summary")
summary_data = []
for coin in coins:
    df = fetch_historical_prices(coin, currency, days)
    if not df.empty:
        max_price = df["price"].max()
        min_price = df["price"].min()
        avg_price = df["price"].mean()
        price_change = (df["price"].iloc[-1] - df["price"].iloc[0]) / df["price"].iloc[0] * 100
        summary_data.append([coin.title(), max_price, min_price, avg_price, price_change])

if summary_data:
    summary_df = pd.DataFrame(summary_data, columns=["Coin", "Max Price", "Min Price", "Avg Price", "Price Change (%)"])
    st.write(summary_df)

# --- AUTO REFRESH LOGIC ---
if manual_refresh:
    st.rerun()  # Refresh manually when button is clicked

if refresh_interval > 0:
    with st.sidebar:
        st.info(f"Refreshing every {refresh_interval} seconds...")
        time.sleep(refresh_interval + 10)  # Add extra delay to avoid hitting rate limits
        st.rerun()  # Refresh automatically after the set interval
