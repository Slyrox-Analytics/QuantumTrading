import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timezone
import uuid
import plotly.express as px
import plotly.graph_objects as go


# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="QuantumTrading Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_FILE = "trades.json"
APP_NAME = "QuantumTrading Terminal"


# =========================
# CYBERPUNK THEME
# =========================
CYBER_CSS = """
<style>
/* --- Base --- */
html, body, [class*="css"]  {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace !important;
}

.stApp {
  background: radial-gradient(1200px 800px at 30% 0%, rgba(0,255,225,0.10), rgba(0,0,0,1) 55%),
              radial-gradient(900px 700px at 80% 10%, rgba(255,0,140,0.10), rgba(0,0,0,1) 60%),
              linear-gradient(180deg, rgba(0,0,0,1), rgba(5,10,20,1));
  color: #d7fff7;
}

/* --- Sidebar --- */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(5,10,20,0.95), rgba(0,0,0,0.95));
  border-right: 1px solid rgba(0,255,225,0.25);
  box-shadow: 0 0 30px rgba(0,255,225,0.05) inset;
}

/* --- Headers --- */
h1, h2, h3, h4 {
  letter-spacing: 0.5px;
}

.qt-title {
  font-size: 40px;
  font-weight: 800;
  letter-spacing: 1px;
  margin: 0 0 8px 0;
  text-shadow: 0 0 12px rgba(0,255,225,0.25);
}

.qt-sub {
  opacity: 0.85;
  margin: 0 0 16px 0;
}

/* --- HUD Cards --- */
.qt-card {
  border: 1px solid rgba(0,255,225,0.25);
  background: linear-gradient(180deg, rgba(0,255,225,0.08), rgba(0,0,0,0.25));
  box-shadow: 0 0 30px rgba(0,255,225,0.06);
  border-radius: 18px;
  padding: 16px 16px 12px 16px;
}

.qt-card-red {
  border: 1px solid rgba(255,0,140,0.25);
  background: linear-gradient(180deg, rgba(255,0,140,0.08), rgba(0,0,0,0.25));
  box-shadow: 0 0 30px rgba(255,0,140,0.06);
}

/* --- Buttons --- */
.stButton>button {
  border-radius: 14px;
  border: 1px solid rgba(0,255,225,0.35);
  background: rgba(0,255,225,0.08);
  color: #d7fff7;
  padding: 10px 14px;
  box-shadow: 0 0 18px rgba(0,255,225,0.06);
}
.stButton>button:hover {
  border: 1px solid rgba(0,255,225,0.70);
  background: rgba(0,255,225,0.14);
  box-shadow: 0 0 28px rgba(0,255,225,0.12);
}

/* --- Inputs --- */
div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea {
  border-radius: 14px !important;
  border: 1px solid rgba(0,255,225,0.25) !important;
  background: rgba(0,0,0,0.35) !important;
  color: #d7fff7 !important;
}
div[data-baseweb="select"] > div {
  border-radius: 14px !important;
  border: 1px solid rgba(0,255,225,0.25) !important;
  background: rgba(0,0,0,0.35) !important;
  color: #d7fff7 !important;
}

/* --- DataFrame --- */
div[data-testid="stDataFrame"] {
  border-radius: 18px;
  overflow: hidden;
  border: 1px solid rgba(0,255,225,0.22);
}

/* --- Subtle scanlines overlay --- */
.qt-scanlines:before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(
    to bottom,
    rgba(255,255,255,0.02),
    rgba(255,255,255,0.02) 1px,
    rgba(0,0,0,0) 3px,
    rgba(0,0,0,0) 6px
  );
  mix-blend-mode: overlay;
  opacity: 0.18;
}

/* --- Small text tweaks --- */
small, .qt-muted { opacity: 0.8; }
</style>
<div class="qt-scanlines"></div>
"""
st.markdown(CYBER_CSS, unsafe_allow_html=True)


# =========================
# HELPERS
# =========================
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_load_trades() -> list:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def safe_save_trades(trades: list) -> None:
    # Note: Streamlit Community Cloud uses ephemeral filesystem on redeploy.
    # This still works for normal usage; for long-term persistence later we can switch to SQLite or a hosted DB.
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)


def to_df(trades: list) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    # Ensure columns exist
    for col in ["timestamp", "pair", "setup", "session", "side", "rr", "pnl", "result", "emotion", "notes", "tags"]:
        if col not in df.columns:
            df[col] = None
    # Types
    df["rr"] = pd.to_numeric(df["rr"], errors="coerce")
    df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce")
    return df


def hud_metric(label: str, value: str, delta: str = ""):
    st.markdown(
        f"""
        <div class="qt-card">
          <div class="qt-muted" style="font-size: 12px;">{label}</div>
          <div style="font-size: 28px; font-weight: 800; margin-top: 6px;">{value}</div>
          <div class="qt-muted" style="font-size: 12px; margin-top: 6px;">{delta}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def compute_stats(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0.0,
            "total_pnl": 0.0,
            "avg_rr": 0.0,
            "avg_pnl": 0.0,
            "best_setup": "",
            "worst_setup": "",
            "streak": 0,
        }

    wins = int((df["result"] == "Win").sum())
    losses = int((df["result"] == "Loss").sum())
    trades = len(df)
    winrate = round((wins / trades) * 100, 2) if trades else 0.0
    total_pnl = float(df["pnl"].fillna(0).sum())
    avg_rr = float(df["rr"].dropna().mean()) if df["rr"].dropna().size else 0.0
    avg_pnl = float(df["pnl"].dropna().mean()) if df["pnl"].dropna().size else 0.0

    # Setup performance
    setup_group = df.groupby("setup", dropna=False)["pnl"].sum().sort_values(ascending=False)
    best_setup = str(setup_group.index[0]) if len(setup_group) else ""
    worst_setup = str(setup_group.index[-1]) if len(setup_group) else ""

    # Streak (last consecutive wins)
    streak = 0
    for r in df["result"].fillna("").tolist()[::-1]:
        if r == "Win":
            streak += 1
        else:
            break

    return {
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "total_pnl": total_pnl,
        "avg_rr": round(avg_rr, 2),
        "avg_pnl": round(avg_pnl, 2),
        "best_setup": best_setup,
        "worst_setup": worst_setup,
        "streak": streak,
    }


def equity_curve(df: pd.DataFrame) -> go.Figure:
    d = df.copy()
    d["pnl"] = d["pnl"].fillna(0)
    d["equity"] = d["pnl"].cumsum()
    fig = px.line(d, y="equity", template="plotly_dark")
    fig.update_traces(line=dict(width=3))
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="",
        yaxis_title="Equity",
        height=320,
    )
    return fig


def pnl_by_bucket(df: pd.DataFrame, col: str) -> go.Figure:
    d = df.copy()
    d[col] = d[col].fillna("—")
    agg = d.groupby(col)["pnl"].sum().sort_values(ascending=False).reset_index()
    fig = px.bar(agg, x=col, y="pnl", template="plotly_dark")
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="",
        yaxis_title="PnL",
        height=320,
    )
    return fig


# =========================
# LOAD STATE
# =========================
if "trades" not in st.session_state:
    st.session_state.trades = safe_load_trades()

df = to_df(st.session_state.trades)
stats = compute_stats(df)

# =========================
# HEADER
# =========================
st.markdown(f'<div class="qt-title">⚡ {APP_NAME}</div>', unsafe_allow_html=True)
st.markdown('<div class="qt-sub qt-muted">Cyberpunk logbook + analytics for crypto scalp trading. Mobile-ready.</div>', unsafe_allow_html=True)

# =========================
# SIDEBAR NAV
# =========================
st.sidebar.markdown("## Navigation")
page = st.sidebar.radio(
    "Go",
    ["Dashboard", "New Trade", "Logbook", "Analytics", "Settings"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Stats")
st.sidebar.metric("Trades", stats["trades"])
st.sidebar.metric("Winrate", f'{stats["winrate"]}%')
st.sidebar.metric("Total PnL", f'{stats["total_pnl"]:.2f}')

# =========================
# PAGES
# =========================
if page == "Dashboard":
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        hud_metric("TRADES", str(stats["trades"]), f'W {stats["wins"]} / L {stats["losses"]}')
    with c2:
        hud_metric("WINRATE", f'{stats["winrate"]}%', f'Streak: {stats["streak"]} win(s)')
    with c3:
        hud_metric("TOTAL PnL", f'{stats["total_pnl"]:.2f}', f'Avg PnL: {stats["avg_pnl"]:.2f}')
    with c4:
        hud_metric("AVG RR", f'{stats["avg_rr"]:.2f}', f'Best setup: {stats["best_setup"]}')

    st.markdown("---")

    left, right = st.columns([1.3, 1])
    with left:
        st.markdown("### Equity Curve")
        if df.empty:
            st.info("No trades yet. Add your first trade in **New Trade**.")
        else:
            st.plotly_chart(equity_curve(df), use_container_width=True)

    with right:
        st.markdown("### PnL by Session")
        if df.empty:
            st.info("Waiting for data.")
        else:
            st.plotly_chart(pnl_by_bucket(df, "session"), use_container_width=True)

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        st.markdown("### PnL by Setup")
        if df.empty:
            st.info("Waiting for data.")
        else:
            st.plotly_chart(pnl_by_bucket(df, "setup"), use_container_width=True)
    with b:
        st.markdown("### PnL by Pair")
        if df.empty:
            st.info("Waiting for data.")
        else:
            st.plotly_chart(pnl_by_bucket(df, "pair"), use_container_width=True)

elif page == "New Trade":
    st.markdown("### Add Trade")
    st.markdown('<div class="qt-muted">Log the trade like a pro. Quick + consistent beats perfect.</div>', unsafe_allow_html=True)

    colA, colB, colC = st.columns([1, 1, 1])
    with colA:
        pair = st.text_input("Pair (e.g. BTCUSDT)", placeholder="BTCUSDT")
        setup = st.text_input("Setup (e.g. SMC FVG)", placeholder="SMC FVG")
        session = st.selectbox("Session", ["US Open", "London", "Asia", "NY Mid", "Other"])
    with colB:
        side = st.selectbox("Side", ["Long", "Short"])
        rr = st.number_input("RR", step=0.1, value=0.0)
        result = st.selectbox("Result", ["Win", "Loss"])
    with colC:
        pnl = st.number_input("PnL (USDT)", step=0.1, value=0.0)
        emotion = st.slider("Emotion (0=ice cold, 10=tilted)", 0, 10, 3)
        tags = st.text_input("Tags (comma separated)", placeholder="impulse, fvg, chop")

    notes = st.text_area("Notes (what mattered?)", placeholder="Trigger, context, execution, mistake, lesson...")

    st.markdown("---")

    save_col, reset_col = st.columns([1, 1])
    with save_col:
        if st.button("💾 Save Trade"):
            trade = {
                "id": str(uuid.uuid4())[:8],
                "timestamp": utc_now_iso(),
                "pair": pair.strip(),
                "setup": setup.strip(),
                "session": session,
                "side": side,
                "rr": float(rr),
                "result": result,
                "pnl": float(pnl),
                "emotion": int(emotion),
                "tags": [t.strip() for t in tags.split(",") if t.strip()] if tags else [],
                "notes": notes.strip(),
            }
            st.session_state.trades.append(trade)
            safe_save_trades(st.session_state.trades)
            st.success("Trade saved.")
            st.rerun()

    with reset_col:
        if st.button("🧹 Reset Form"):
            st.rerun()

elif page == "Logbook":
    st.markdown("### Logbook")
    st.markdown('<div class="qt-muted">Filter, review, export. This is your edge engine.</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("No trades logged yet.")
    else:
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            f_pair = st.selectbox("Filter Pair", ["All"] + sorted(df["pair"].fillna("—").unique().tolist()))
        with f2:
            f_setup = st.selectbox("Filter Setup", ["All"] + sorted(df["setup"].fillna("—").unique().tolist()))
        with f3:
            f_session = st.selectbox("Filter Session", ["All"] + sorted(df["session"].fillna("—").unique().tolist()))
        with f4:
            f_result = st.selectbox("Filter Result", ["All", "Win", "Loss"])

        view = df.copy()
        if f_pair != "All":
            view = view[view["pair"].fillna("—") == f_pair]
        if f_setup != "All":
            view = view[view["setup"].fillna("—") == f_setup]
        if f_session != "All":
            view = view[view["session"].fillna("—") == f_session]
        if f_result != "All":
            view = view[view["result"] == f_result]

        view = view.sort_values("timestamp", ascending=False)

        st.dataframe(
            view[["timestamp", "pair", "session", "setup", "side", "rr", "result", "pnl", "emotion", "tags", "notes"]],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("---")
        st.markdown("### Manage")
        m1, m2, m3 = st.columns([1, 1, 1])

        with m1:
            st.download_button(
                "⬇️ Export JSON",
                data=json.dumps(st.session_state.trades, ensure_ascii=False, indent=2),
                file_name="quantumtrading_trades.json",
                mime="application/json",
            )
        with m2:
            st.download_button(
                "⬇️ Export CSV",
                data=view.to_csv(index=False).encode("utf-8"),
                file_name="quantumtrading_trades.csv",
                mime="text/csv",
            )
        with m3:
            if st.button("🗑️ Delete ALL Trades (danger)"):
                st.session_state.trades = []
                safe_save_trades([])
                st.warning("All trades deleted.")
                st.rerun()

elif page == "Analytics":
    st.markdown("### Analytics")
    st.markdown('<div class="qt-muted">Your performance map: where you win, where you bleed.</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("No trades logged yet.")
    else:
        # KPI row
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            hud_metric("BEST SETUP", stats["best_setup"] or "—", "PnL based ranking")
        with c2:
            hud_metric("WORST SETUP", stats["worst_setup"] or "—", "Fix this or avoid it")
        with c3:
            hud_metric("AVG PnL", f'{stats["avg_pnl"]:.2f}', "per trade")
        with c4:
            hud_metric("TILT AVG", f'{df["emotion"].dropna().mean():.2f}', "lower is better")

        st.markdown("---")

        # Setup table
        st.markdown("### Setup Performance")
        setup_perf = (
            df.groupby("setup", dropna=False)
            .agg(
                trades=("id", "count"),
                wins=("result", lambda x: (x == "Win").sum()),
                pnl=("pnl", "sum"),
                avg_pnl=("pnl", "mean"),
                avg_rr=("rr", "mean"),
                avg_emotion=("emotion", "mean"),
            )
            .reset_index()
        )
        setup_perf["winrate"] = (setup_perf["wins"] / setup_perf["trades"] * 100).round(2)
        setup_perf = setup_perf.sort_values("pnl", ascending=False)

        st.dataframe(setup_perf, use_container_width=True, hide_index=True)

        st.markdown("---")
        l, r = st.columns(2)
        with l:
            st.markdown("### Result Distribution")
            dist = df["result"].value_counts().reset_index()
            dist.columns = ["result", "count"]
            fig = px.pie(dist, names="result", values="count", template="plotly_dark")
            fig.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                height=320,
            )
            st.plotly_chart(fig, use_container_width=True)

        with r:
            st.markdown("### Emotion vs PnL")
            d = df.copy()
            d["emotion"] = pd.to_numeric(d["emotion"], errors="coerce")
            fig = px.scatter(d, x="emotion", y="pnl", hover_data=["pair", "setup", "session"], template="plotly_dark")
            fig.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                height=320,
            )
            st.plotly_chart(fig, use_container_width=True)

elif page == "Settings":
    st.markdown("### Settings")
    st.markdown('<div class="qt-muted">Tuning + maintenance.</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Import trades (JSON)")
    up = st.file_uploader("Upload quantumtrading_trades.json", type=["json"])
    if up is not None:
        try:
            incoming = json.loads(up.read().decode("utf-8"))
            if isinstance(incoming, list):
                st.session_state.trades = incoming
                safe_save_trades(incoming)
                st.success("Imported trades.")
                st.rerun()
            else:
                st.error("Invalid file format: expected a JSON array.")
        except Exception as e:
            st.error(f"Import failed: {e}")

    st.markdown("---")
    st.markdown("#### Notes")
    st.info(
        "Streamlit Community Cloud can reset local files on redeploy. "
        "If you want bulletproof persistence, we’ll switch to SQLite (still easy) "
        "or a tiny hosted DB. Export JSON regularly as a backup."
    )
