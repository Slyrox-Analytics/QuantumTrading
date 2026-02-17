import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.express as px

# ================= LOGIN PROTECTION =================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Login")

    pw = st.text_input("Passwort", type="password")

    if st.button("Login"):
        if pw == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Falsches Passwort")

    st.stop()
# ====================================================

from components.charts import tradingview_widget


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

def get_futures_price(symbol):
    try:
        url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        data = r.json()
        if "price" in data:
            return float(data["price"])
        return None
    except Exception as e:
        return None

# ===== NOTES STORAGE =====
NOTES_FILE = "notes.json"
IMG_FOLDER = "notes_images"

def load_notes():
    url = f"https://api.github.com/repos/{REPO}/contents/{NOTES_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode()
        return json.loads(content)
    return []

def save_notes(data):
    url = f"https://api.github.com/repos/{REPO}/contents/{NOTES_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    sha = r.json()["sha"] if r.status_code == 200 else None
    encoded = base64.b64encode(json.dumps(data, indent=2).encode()).decode()
    requests.put(url, headers=headers, json={
        "message": "update notes",
        "content": encoded,
        "sha": sha
    })

def upload_note_file(file, folder):
    filename = f"{int(datetime.now().timestamp())}_{file.name}"
    url = f"https://api.github.com/repos/{REPO}/contents/{folder}/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    content = base64.b64encode(file.read()).decode()

    requests.put(url, headers=headers, json={
        "message": "upload file",
        "content": content
    })

    return f"https://raw.githubusercontent.com/{REPO}/main/{folder}/{filename}"

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
st.title("Trading Terminal")
st.caption("Trading logbook + analytics")

# ---------------- SIDEBAR ----------------
page=st.sidebar.radio("Navigation",["Dashboard","New Trade","Logbook","Analytics","Sonstiges","Charts"])
st.sidebar.metric("Trades",total)
st.sidebar.metric("Total PnL",pnl)
st.sidebar.metric("Avg ROI", f"{avg_roi:.2f}%")

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
if page=="New Trade":

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

• Equity Curve = kumulierte PnL Entwicklung  
• CSV Export speichert exakt das Logbook

---

### Eigene Notizen
📊 Marktstruktur – SMC Basics

BoS (Break of Structure)
→ Markt bricht vorheriges High/Low
→ bestätigt Trendfortsetzung

CHoCH (Change of Character)
→ erster Bruch gegen aktuellen Trend
→ mögliches Trend-Ende / Reversal Signal

👉 Regel
BoS = Trend bestätigt
CHoCH = Trend könnte wechseln

🧱 Order Blocks

Bullish OB (Support)
→ letzte rote Kerze vor starkem Move nach oben
→ mögliche Reaktionszone für Longs

Bearish OB (Resistance)
→ letzte grüne Kerze vor starkem Move nach unten
→ mögliche Short-Zone

👉 Wichtig
OB ≠ Entry
OB = Reaktionsbereich

🌊 Fair Value Gap (FVG)

→ ineffizienter Preisbereich zwischen 3 Kerzen
→ Markt kehrt oft zurück um Gap zu „füllen“

Nutzen:
Entry Zone
TP Target
Confirmation Level

📈 Heiken Ashi Zweck

Nicht für Entry — nur für Trendvisualisierung

Hilft bei:
Trendrichtung erkennen
Noise filtern
Momentum sehen

🔥 Heatmap / DOM (Orderflow)

Zeigt reale Orders im Markt

Wichtige Signale:
große Limit Orders → Support/Resistance
aggressive Market Orders → Momentum
Delta Imbalance → Käufer vs Verkäufer Stärke

🎯 Entry-Bestätigung (High Probability Setup)

Trade nur wenn:

✔ Strukturbruch (BoS oder CHoCH)
✔ Reaktion an OB oder FVG
✔ Orderflow bestätigt Richtung
✔ klares CRV ≥ 2

Wenn eins fehlt → kein Trade

🧠 Regelwerk (Mindset Filter)

kein Setup → kein Trade
kein Confirmation → kein Entry
Emotion ≠ Signal
""")

    st.divider()
    st.subheader("📸 Screenshot Notizen")

    notes = load_notes()

    img = st.file_uploader("Screenshot hochladen", type=["png","jpg","jpeg"])
    text = st.text_area("Notiz")

    if st.button("Speichern Screenshot"):
        if img:
            url = upload_note_file(img,"notes_images")
            notes.append({"img": url, "text": text})
            save_notes(notes)
            st.rerun()

    for n in reversed(notes):
        if "img" in n:
            st.image(n["img"], use_container_width=True)

        if "video" in n:
            st.video(n["video"])

        if n.get("text"):
            st.markdown(n["text"])

        st.divider()


# =========================
# CHARTS PAGE
# =========================
elif page == "Charts":



    # --- Ticker oben ---
    st.components.v1.html("""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript"
      src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js"
      async>
      {
        "symbols": [
          {"proName":"BINANCE:BTCUSDT.P","title":"BTC"},
          {"proName":"BINANCE:SOLUSDT.P","title":"SOL"}
        ],
        "showSymbolLogo": true,
        "isTransparent": true,
        "displayMode":"adaptive",
        "colorTheme":"dark",
        "locale":"en"
      }
      </script>
    </div>
    """, height=80)

    st.subheader("Live Charts")

    # --- BTC Chart ---
    tradingview_widget("BINANCE:BTCUSDT.P", height=450)

    # --- SOL Chart ---
    tradingview_widget("BINANCE:SOLUSDT.P", height=450)

