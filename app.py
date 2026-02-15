import streamlit as st
import pandas as pd
import json
import os
import uuid
from datetime import datetime
import plotly.express as px

# ---------------- CONFIG ----------------
st.set_page_config(page_title="QuantumTrading", layout="wide")
DATA_FILE = "trades.json"

# ---------------- STYLE ----------------
st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at 20% 0%, rgba(0,255,200,0.15), transparent 40%),
                radial-gradient(circle at 80% 0%, rgba(0,140,255,0.15), transparent 40%),
                #020409;
    color:#d7fff7;
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#03121a,#02060a);
    border-right:1px solid rgba(0,255,200,0.4);
}
section[data-testid="stSidebar"] * {
    color:#9ffcff !important;
}
section[data-testid="stSidebar"] div[data-testid="stMetricValue"] {
    color:#00ffd0 !important;
    font-weight:bold;
}
label {
    color:#00ffd0 !important;
    font-weight:600 !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextArea"] textarea {
    background:#02141c !important;
    color:#cfffff !important;
    border:1px solid rgba(0,255,200,0.6) !important;
}
div[data-baseweb="select"] > div {
    background:#02141c !important;
    border:1px solid rgba(0,255,200,0.6) !important;
    color:#cfffff !important;
}
.stButton button {
    background:#02141c;
    border:1px solid rgba(0,255,200,0.6);
    color:#9ffcff;
}
.stButton button:hover {
    background:#03232c;
    border:1px solid #00ffd0;
    box-shadow:0 0 12px rgba(0,255,200,0.4);
}
.card {
    border:1px solid rgba(0,255,200,0.4);
    padding:15px;
    border-radius:15px;
    background:rgba(0,255,200,0.05);
    text-align:center;
}
</style>
""", unsafe_allow_html=True)

# ---------------- DATA ----------------
def load_trades():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE,"r") as f:
            return json.load(f)
    return []

def save_trades(data):
    with open(DATA_FILE,"w") as f:
        json.dump(data,f,indent=2)

trades = load_trades()
df = pd.DataFrame(trades)

# ---------------- STATS ----------------
def stats(df):
    if df.empty:
        return 0,0,0,0,0
    wins = len(df[df.pnl > 0])
    losses = len(df[df.pnl < 0])
    total = len(df)
    pnl = df.pnl.sum()
    winrate = round((wins/total)*100,2)
    return total,wins,losses,winrate,pnl

total,wins,losses,winrate,pnl = stats(df)

# ---------------- HEADER ----------------
st.title("⚡ QuantumTrading Terminal")
st.caption("Trading logbook + analytics")

# ---------------- SIDEBAR ----------------
page = st.sidebar.radio("Navigation",
    ["Dashboard","New Trade","Logbook","Analytics"]
)

st.sidebar.markdown("### Quick Stats")
st.sidebar.metric("Trades", total)
st.sidebar.metric("Winrate", f"{winrate}%")
st.sidebar.metric("Total PnL", pnl)

# =====================================================
# DASHBOARD
# =====================================================
if page == "Dashboard":

    c1,c2,c3,c4,c5 = st.columns(5)

    with c1:
        st.markdown(f'<div class="card"><h3>Trades</h3><h2>{total}</h2></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="card"><h3>Wins</h3><h2>{wins}</h2></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="card"><h3>Losses</h3><h2>{losses}</h2></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="card"><h3>Winrate</h3><h2>{winrate}%</h2></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="card"><h3>Total PnL</h3><h2>{pnl}</h2></div>', unsafe_allow_html=True)

    st.divider()

    # ---------- PIE CHART ----------
    if total > 0:

        pie_df = pd.DataFrame({
            "Result":["Wins","Losses"],
            "Count":[wins,losses]
        })

        fig = px.pie(
            pie_df,
            names="Result",
            values="Count",
            hole=0.6,
            color="Result",
            color_discrete_map={
                "Wins":"#00ffd0",
                "Losses":"#ff3b5c"
            }
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#d7fff7",
            legend_title=""
        )

        st.plotly_chart(fig, use_container_width=True)

    # ---------- EQUITY CURVE ----------
    if not df.empty:
        df["equity"] = df.pnl.cumsum()
        fig2 = px.line(df, y="equity", template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

# =====================================================
# NEW TRADE
# =====================================================
elif page == "New Trade":

    pair = st.selectbox("Pair", ["BTCUSDT","SOLUSDT"])

    col1,col2 = st.columns(2)

    with col1:
        side = st.selectbox("Side",["Long","Short"])
    with col2:
        pnl_value = st.number_input("PnL", step=0.1)

    note = st.text_area("Notes")

    if st.button("Save Trade"):

        trade = {
            "id": str(uuid.uuid4())[:8],
            "time": str(datetime.now()),
            "pair": pair,
            "side": side,
            "pnl": pnl_value,
            "note": note
        }

        trades.append(trade)
        save_trades(trades)

        st.success("Trade saved")
        st.rerun()

# =====================================================
# LOGBOOK
# =====================================================
elif page == "Logbook":

    if df.empty:
        st.info("No trades yet")
    else:
        st.dataframe(df, use_container_width=True)

# =====================================================
# ANALYTICS
# =====================================================
elif page == "Analytics":

    if df.empty:
        st.info("No trades yet")
    else:
        st.subheader("PnL by Pair")
        fig = px.bar(df.groupby("pair")["pnl"].sum().reset_index(),
                     x="pair", y="pnl", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
