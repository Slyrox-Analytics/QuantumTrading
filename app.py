import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import plotly.express as px

# ---------------- CONFIG ----------------
st.set_page_config(page_title="QuantumTrading", layout="wide")
DATA_FILE = "trades.json"
TZ = ZoneInfo("Europe/Berlin")

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
label {color:#00ffd0 !important;font-weight:600 !important;}

.card{
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
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_trades(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

trades = load_trades()
df = pd.DataFrame(trades)

# ---------------- CALC ----------------
if not df.empty:
    df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)
    df["margin"] = pd.to_numeric(df["margin"], errors="coerce").fillna(0.0)
    df["roi"] = df.apply(lambda r: (r.pnl/r.margin*100) if r.margin>0 else 0, axis=1)

# ---------------- STATS ----------------
def stats(df):
    if df.empty:
        return 0,0,0,0,0
    wins = int((df["pnl"] > 0).sum())
    losses = int((df["pnl"] < 0).sum())
    total = len(df)
    pnl = float(df["pnl"].sum())
    roi = (df["roi"].mean()) if "roi" in df else 0
    return total,wins,losses,pnl,roi

total,wins,losses,pnl,roi = stats(df)

# ---------------- HEADER ----------------
st.title("⚡ QuantumTrading Terminal")
st.caption("Trading logbook + analytics")

# ---------------- SIDEBAR ----------------
page = st.sidebar.radio("Navigation", ["Dashboard","New Trade","Logbook","Analytics"])

st.sidebar.metric("Trades", total)
st.sidebar.metric("Total PnL", pnl)

if st.sidebar.button("Reset ALL Data"):
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    st.rerun()

# =====================================================
# DASHBOARD
# =====================================================
if page=="Dashboard":

    c1,c2,c3,c4,c5 = st.columns(5)

    with c1: st.markdown(f'<div class="card"><h3>Trades</h3><h2>{total}</h2></div>',unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><h3>Wins</h3><h2>{wins}</h2></div>',unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card"><h3>Losses</h3><h2>{losses}</h2></div>',unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="card"><h3>Total PnL</h3><h2>{pnl:g}</h2></div>',unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="card"><h3>Avg ROI</h3><h2>{roi:.2f}%</h2></div>',unsafe_allow_html=True)

    if not df.empty:

        # Equity Curve
        df["equity"]=df["pnl"].cumsum()
        fig=px.line(df,y="equity",title="Equity Curve")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig,use_container_width=True)

        # Wins vs Losses
        pie=px.pie(names=["Wins","Losses"],values=[wins,losses],hole=0.6,title="Win Ratio")
        pie.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(pie,use_container_width=True)

        # Zeitraum Filter
        days=st.selectbox("Range",[7,30,90,180])
        cutoff=datetime.now(TZ)-timedelta(days=days)

        df["dt"]=pd.to_datetime(df["time"])
        fdf=df[df["dt"]>cutoff]

        if not fdf.empty:
            monthly=fdf.groupby(pd.Grouper(key="dt",freq="D"))["pnl"].sum().cumsum().reset_index()
            mfig=px.area(monthly,x="dt",y="pnl",title="Performance Trend")
            mfig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(mfig,use_container_width=True)

# =====================================================
# NEW TRADE
# =====================================================
elif page=="New Trade":

    pair=st.selectbox("Pair",["BTCUSDT","SOLUSDT"])

    c1,c2,c3=st.columns(3)

    with c1:
        side=st.selectbox("Side",["Long","Short"])
    with c2:
        margin=st.number_input("Margin",step=1.0)
    with c3:
        pnl_value=st.number_input("PnL",step=0.1)

    note=st.text_area("Notes")

    if st.button("Save Trade"):
        trade={
            "id":f"Trade{len(trades)+1}",
            "time":datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "pair":pair,
            "side":side,
            "margin":margin,
            "pnl":pnl_value,
            "note":note
        }
        trades.append(trade)
        save_trades(trades)
        st.rerun()

# =====================================================
# LOGBOOK
# =====================================================
elif page=="Logbook":

    if df.empty:
        st.info("No trades yet")
    else:
        show=df.copy()
        show["roi"]=show["roi"].round(2)
        st.dataframe(show,use_container_width=True)

        csv=show.to_csv(index=False,sep=";",encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("Download CSV",csv,"trades.csv","text/csv")

        delete_id=st.selectbox("Delete Trade",show["id"])
        if st.button("Delete Selected"):
            trades=[t for t in trades if t["id"]!=delete_id]
            save_trades(trades)
            st.rerun()

# =====================================================
# ANALYTICS
# =====================================================
elif page=="Analytics":

    if df.empty:
        st.info("No trades yet")
    else:
        fig=px.bar(df.groupby("pair")["pnl"].sum().reset_index(),x="pair",y="pnl",title="PnL by Pair")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig,use_container_width=True)
