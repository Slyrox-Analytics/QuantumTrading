import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
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
section[data-testid="stSidebar"] * { color:#9ffcff !important; }
label { color:#00ffd0 !important; font-weight:600 !important; }
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextArea"] textarea{
 background:#02141c !important;
 color:#cfffff !important;
 border:1px solid rgba(0,255,200,0.6) !important;
}
div[data-baseweb="select"] > div{
 background:#02141c !important;
 border:1px solid rgba(0,255,200,0.6) !important;
 color:#cfffff !important;
}
.stButton button{
 background:#02141c;
 border:1px solid rgba(0,255,200,0.6);
 color:#9ffcff;
}
.stButton button:hover{
 background:#03232c;
 border:1px solid #00ffd0;
 box-shadow:0 0 12px rgba(0,255,200,0.4);
}
div[data-testid="stDownloadButton"] button{
 background:#02141c !important;
 border:1px solid rgba(0,255,200,0.6) !important;
 color:#9ffcff !important;
}
.card{
 border:1px solid rgba(0,255,200,0.4);
 padding:15px;
 border-radius:15px;
 background:rgba(0,255,200,0.05);
 text-align:center;
}
.qpill-pos{ color:#00ffd0;font-weight:700;}
.qpill-neg{ color:#ff4d6d;font-weight:700;}
</style>
""", unsafe_allow_html=True)

# ---------------- DATA ----------------
import requests
import base64

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = st.secrets["REPO"]
FILE_PATH = "trades.json"

def load_trades():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode()
        return json.loads(content)

    return []

def save_trades(data):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    r = requests.get(url, headers=headers)

    sha = None
    if r.status_code == 200:
        sha = r.json()["sha"]

    encoded = base64.b64encode(json.dumps(data, indent=2).encode()).decode()

    payload = {
        "message": "update trades",
        "content": encoded,
        "sha": sha
    }

    requests.put(url, headers=headers, json=payload)

trades=load_trades()
df=pd.DataFrame(trades)

# ---------------- STATS ----------------
def stats(df):
    if df.empty or "pnl" not in df.columns:
        return 0,0,0,0,0
    df["pnl"]=pd.to_numeric(df["pnl"],errors="coerce").fillna(0)
    df["margin"]=pd.to_numeric(df.get("margin",0),errors="coerce").fillna(0)
    df["roi"]=df.apply(lambda r:(r.pnl/r.margin*100) if r.margin>0 else 0,axis=1)

    wins=int((df.pnl>0).sum())
    losses=int((df.pnl<0).sum())
    total=len(df)
    pnl=float(df.pnl.sum())
    avg_roi=df["roi"].mean()
    return total,wins,losses,pnl,avg_roi

total,wins,losses,pnl,avg_roi=stats(df)

# ---------------- CHART THEME ----------------
def cyberpunk_plot(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#d7fff7"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10,r=10,t=30,b=10)
    )
    fig.update_xaxes(gridcolor="rgba(0,255,200,0.10)")
    fig.update_yaxes(gridcolor="rgba(0,255,200,0.10)")
    return fig

# ---------------- HEADER ----------------
st.title("⚡ QuantumTrading Terminal")
st.caption("Trading logbook + analytics")

# ---------------- SIDEBAR ----------------
page=st.sidebar.radio("Navigation",["Dashboard","New Trade","Logbook","Analytics","Sonstiges"])
st.sidebar.metric("Trades",total)
st.sidebar.metric("Total PnL",pnl)

if st.sidebar.button("Reset ALL Data"):
    save_trades([])
    st.rerun()

# =====================================================
# DASHBOARD
# =====================================================
if page=="Dashboard":

    c1,c2,c3,c4,c5=st.columns(5)
    with c1: st.markdown(f'<div class="card"><h3>Trades</h3><h2>{total}</h2></div>',True)
    with c2: st.markdown(f'<div class="card"><h3>Wins</h3><h2>{wins}</h2></div>',True)
    with c3: st.markdown(f'<div class="card"><h3>Losses</h3><h2>{losses}</h2></div>',True)
    with c4: st.markdown(f'<div class="card"><h3>Total PnL</h3><h2>{pnl:g}</h2></div>',True)
    with c5: st.markdown(f'<div class="card"><h3>Avg ROI</h3><h2>{avg_roi:.2f}%</h2></div>',True)

    if not df.empty:

        df["equity"]=df["pnl"].cumsum()
        fig=px.line(df,y="equity",title="Equity Curve")
        st.plotly_chart(cyberpunk_plot(fig),use_container_width=True)

        pie_df=pd.DataFrame({"Outcome":["Wins","Losses"],"Count":[wins,losses]})
        pie=px.pie(pie_df,names="Outcome",values="Count",hole=0.6,title="Wins vs Losses")
        st.plotly_chart(cyberpunk_plot(pie),use_container_width=True)

        # RANGE FILTER
        days = st.selectbox("Range (Kumulierter PnL in Zeitraum)", [7,30,90,180], index=1)

        df["dt"] = pd.to_datetime(df["time"], errors="coerce")
        df["dt"] = pd.to_datetime(df["time"], errors="coerce", utc=True).dt.tz_convert(TZ)

        cutoff=pd.Timestamp.now(TZ)-pd.Timedelta(days=int(days))
        fdf=df[df["dt"]>=cutoff]

        if not fdf.empty:
            perf=(fdf.groupby(pd.Grouper(key="dt",freq="D"))["pnl"].sum().cumsum().reset_index())
            area=px.area(perf,x="dt",y="pnl",title="Performance Trend")
            st.plotly_chart(cyberpunk_plot(area),use_container_width=True)
        else:
            st.info("No trades in selected range")

# =====================================================
# NEW TRADE
# =====================================================
elif page=="New Trade":

    pair=st.selectbox("Pair",["BTCUSDT","SOLUSDT"])

    col1,col2,col3=st.columns(3)
    with col1: side=st.selectbox("Side",["Long","Short"])
    with col2: margin=st.number_input("Margin",step=1.0)
    with col3: pnl_value=st.number_input("PnL",step=0.1)

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

        def color(v):
            v=float(v)
            return f'<span class="qpill-pos">{v}</span>' if v>0 else f'<span class="qpill-neg">{v}</span>' if v<0 else v

        header="".join([f"<th>{c}</th>" for c in show.columns])
        rows=""
        for _,r in show.iterrows():
            rows+="<tr>"+ "".join([f"<td>{color(r[c]) if c=='pnl' else r[c]}</td>" for c in show.columns])+"</tr>"

        st.markdown(f"""
        <table style="width:100%;border-collapse:collapse">
        <thead style="background:rgba(0,255,200,0.08)">{header}</thead>
        <tbody>{rows}</tbody>
        </table>
        """,unsafe_allow_html=True)

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
        st.plotly_chart(cyberpunk_plot(fig),use_container_width=True)

# =====================================================
# SONSTIGES
# =====================================================
elif page=="Sonstiges":

    st.header("Sonstiges / Infos")

    st.markdown("""
### Erklärung der Kennzahlen

**PnL (Profit & Loss)**
→ Gewinn oder Verlust eines Trades in $

**ROI (Return on Investment)**
→ Rendite basierend auf eingesetzter Margin  
Formel:
ROI = Gewinn ÷ Margin × 100

---

### Hinweise

• Range Filter zeigt nur Trades innerhalb der gewählten Tage  
• Equity Curve = kumulierte PnL Entwicklung  
• CSV Export speichert exakt das Logbook

---

### Eigene Notizen
Hier kannst du jederzeit Code-Notizen oder Trading-Regeln eintragen.
""")
