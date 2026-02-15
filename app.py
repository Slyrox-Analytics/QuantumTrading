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
section[data-testid="stSidebar"] * {
  color:#9ffcff !important;
}
label {
  color:#00ffd0 !important;
  font-weight:600 !important;
}

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

/* Normal Buttons */
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

/* Download Button */
div[data-testid="stDownloadButton"] button{
  background:#02141c !important;
  border:1px solid rgba(0,255,200,0.6) !important;
  color:#9ffcff !important;
}
div[data-testid="stDownloadButton"] button:hover{
  background:#03232c !important;
  border:1px solid #00ffd0 !important;
  box-shadow:0 0 12px rgba(0,255,200,0.4) !important;
}

.card{
  border:1px solid rgba(0,255,200,0.4);
  padding:15px;
  border-radius:15px;
  background:rgba(0,255,200,0.05);
  text-align:center;
}

/* Dark Table (Logbook) */
.qtable-wrap{
  border:1px solid rgba(0,255,200,0.35);
  border-radius:14px;
  overflow:hidden;
  background:rgba(0,0,0,0.25);
}
table.qtable{
  width:100%;
  border-collapse:collapse;
  font-size:14px;
}
table.qtable thead th{
  text-align:left;
  padding:12px 12px;
  background:rgba(0,255,200,0.08);
  color:#9ffcff;
  border-bottom:1px solid rgba(0,255,200,0.25);
}
table.qtable tbody td{
  padding:10px 12px;
  color:#d7fff7;
  border-bottom:1px solid rgba(0,255,200,0.10);
}
table.qtable tbody tr:hover td{
  background:rgba(0,255,200,0.06);
}
.qpill-pos{
  color:#00ffd0;
  font-weight:700;
}
.qpill-neg{
  color:#ff4d6d;
  font-weight:700;
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

# ---------------- STATS ----------------
def stats(df):
    if df.empty or "pnl" not in df.columns:
        return 0, 0, 0, 0
    df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)
    wins = int((df["pnl"] > 0).sum())
    losses = int((df["pnl"] < 0).sum())
    total = int(len(df))
    pnl = float(df["pnl"].sum())
    return total, wins, losses, pnl

total, wins, losses, pnl = stats(df)

# ---------------- HELPERS ----------------
def cyberpunk_plot(fig):
    # Transparent background so it blends with your page (fixes the "white chart" problem)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#d7fff7"),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,255,200,0.25)",
            borderwidth=1
        ),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    # Softer grid, still readable
    fig.update_xaxes(gridcolor="rgba(0,255,200,0.10)", zerolinecolor="rgba(0,255,200,0.15)")
    fig.update_yaxes(gridcolor="rgba(0,255,200,0.10)", zerolinecolor="rgba(0,255,200,0.15)")
    return fig

def render_logbook_table(df_show: pd.DataFrame):
    show = df_show.copy()
    # nicer time display
    if "time" in show.columns:
        show["time"] = show["time"].astype(str)

    # pnl pill coloring via HTML
    def fmt_pnl(x):
        try:
            v = float(x)
        except:
            v = 0.0
        cls = "qpill-pos" if v > 0 else ("qpill-neg" if v < 0 else "")
        return f'<span class="{cls}">{v:g}</span>'

    cols = ["id", "time", "pair", "side", "pnl", "note"]
    cols = [c for c in cols if c in show.columns]
    show = show[cols]

    # build html table
    thead = "".join([f"<th>{c}</th>" for c in cols])
    rows = []
    for _, r in show.iterrows():
        tds = []
        for c in cols:
            val = r.get(c, "")
            if c == "pnl":
                tds.append(f"<td>{fmt_pnl(val)}</td>")
            else:
                safe = "" if pd.isna(val) else str(val)
                tds.append(f"<td>{safe}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")

    html = f"""
    <div class="qtable-wrap">
      <table class="qtable">
        <thead><tr>{thead}</tr></thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.title("⚡ QuantumTrading Terminal")
st.caption("Trading logbook + analytics")

# ---------------- SIDEBAR ----------------
page = st.sidebar.radio("Navigation", ["Dashboard", "New Trade", "Logbook", "Analytics"])

st.sidebar.markdown("### Quick Stats")
st.sidebar.metric("Trades", total)
st.sidebar.metric("Total PnL", pnl)

# RESET BUTTON
if st.sidebar.button("Reset ALL Data"):
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    st.rerun()

# =====================================================
# DASHBOARD
# =====================================================
if page == "Dashboard":
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f'<div class="card"><h3>Trades</h3><h2>{total}</h2></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="card"><h3>Wins</h3><h2>{wins}</h2></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="card"><h3>Losses</h3><h2>{losses}</h2></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="card"><h3>Total PnL</h3><h2>{pnl:g}</h2></div>', unsafe_allow_html=True)

    st.divider()

    if not df.empty:
        df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)
        df["equity"] = df["pnl"].cumsum()

        fig = px.line(df, y="equity", template="plotly_dark", title="Equity Curve")
        fig = cyberpunk_plot(fig)
        st.plotly_chart(fig, use_container_width=True)

        pie_df = pd.DataFrame({"Outcome": ["Wins", "Losses"], "Count": [wins, losses]})
        pie = px.pie(pie_df, names="Outcome", values="Count", hole=0.6, template="plotly_dark", title="Wins vs Losses")
        pie = cyberpunk_plot(pie)
        st.plotly_chart(pie, use_container_width=True)
    else:
        st.info("No trades yet")

# =====================================================
# NEW TRADE
# =====================================================
elif page == "New Trade":
    pair = st.selectbox("Pair", ["BTCUSDT", "SOLUSDT"])

    col1, col2 = st.columns(2)
    with col1:
        side = st.selectbox("Side", ["Long", "Short"])
    with col2:
        pnl_value = st.number_input("PnL", step=0.1)

    note = st.text_area("Notes")

    if st.button("Save Trade"):
        trade = {
            "id": f"Trade{len(trades) + 1}",
            "time": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "pair": pair,
            "side": side,
            "pnl": float(pnl_value),
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
        render_logbook_table(df)

        # Proper CSV (columns -> cells)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "trades.csv", "text/csv")

        delete_id = st.selectbox("Delete Trade", df["id"])
        if st.button("Delete Selected"):
            trades = [t for t in trades if t.get("id") != delete_id]
            save_trades(trades)
            st.rerun()

# =====================================================
# ANALYTICS
# =====================================================
elif page == "Analytics":
    if df.empty:
        st.info("No trades yet")
    else:
        st.subheader("PnL by Pair")
        df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)
        fig = px.bar(
            df.groupby("pair")["pnl"].sum().reset_index(),
            x="pair",
            y="pnl",
            template="plotly_dark"
        )
        fig = cyberpunk_plot(fig)
        st.plotly_chart(fig, use_container_width=True)
