import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

st.set_page_config(page_title="QuantumTrading", layout="wide")

DATA_FILE = "trades.json"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        trades = json.load(f)
else:
    trades = []

st.markdown("""
<style>
body { background-color: black; color: #00ffe1; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ QuantumTrading Terminal")

st.sidebar.header("New Trade")

pair = st.sidebar.text_input("Pair")
setup = st.sidebar.text_input("Setup")
rr = st.sidebar.number_input("RR", step=0.1)
result = st.sidebar.selectbox("Result", ["Win", "Loss"])
pnl = st.sidebar.number_input("PnL")

if st.sidebar.button("Save Trade"):
    trades.append({
        "Pair": pair,
        "Setup": setup,
        "RR": rr,
        "Result": result,
        "PnL": pnl
    })
    with open(DATA_FILE, "w") as f:
        json.dump(trades, f)
    st.sidebar.success("Saved")

df = pd.DataFrame(trades)

if not df.empty:

    wins = len(df[df.Result == "Win"])
    winrate = round((wins / len(df)) * 100, 2)
    total_pnl = df.PnL.sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Trades", len(df))
    col2.metric("Winrate", f"{winrate}%")
    col3.metric("Total PnL", total_pnl)

    st.subheader("Equity Curve")
    df["Equity"] = df.PnL.cumsum()
    fig = px.line(df, y="Equity")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Trade Log")
    st.dataframe(df, use_container_width=True)

else:
    st.info("No trades yet.")
