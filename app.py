
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config("CycleSense Dashboard", layout="wide", page_icon="🌀")

CARDS_CSV = Path("cards_min.csv")
BLACK_CSV = Path("black_cards.csv")

@st.cache_data
def load_cards():
    if CARDS_CSV.exists():
        df = pd.read_csv(CARDS_CSV)
        df["CardID"] = df["CardID"].astype(str)
        return df
    return pd.DataFrame(columns=["CardID","Phase","EquityReturn","DebtReturn","GoldReturn","CashReturn","Notes"])

@st.cache_data
def load_black():
    if BLACK_CSV.exists():
        df = pd.read_csv(BLACK_CSV)
        df["BlackID"] = df["BlackID"].astype(str)
        return df
    return pd.DataFrame(columns=["BlackID","Label","EqAdj","DebtAdj","GoldAdj","CashAdj","Notes"])

cards_df = load_cards()
black_df = load_black()

if "teams" not in st.session_state:
    st.session_state.teams = ["Team A", "Team B", "Team C"]
if "nav" not in st.session_state:
    st.session_state.nav = {t: 10.0 for t in st.session_state.teams}
if "history" not in st.session_state:
    st.session_state.history = []
if "round" not in st.session_state:
    st.session_state.round = 1

st.sidebar.header("Round Controls")
phase = st.sidebar.selectbox("Phase (Deck Color)", ["Green","Blue","Orange","Red","Black"], index=0)
card_id_options = ["Manual"] + sorted(cards_df[cards_df["Phase"]==phase]["CardID"].unique().tolist())
card_id = st.sidebar.selectbox("Card", card_id_options, index=0)

prefill = {"eq":0.0,"debt":0.0,"gold":0.0,"cash":0.0,"note":""}
if card_id != "Manual":
    row = cards_df[cards_df["CardID"]==card_id].iloc[0].to_dict()
    prefill = {
        "eq": float(row.get("EquityReturn",0)),
        "debt": float(row.get("DebtReturn",0)),
        "gold": float(row.get("GoldReturn",0)),
        "cash": float(row.get("CashReturn",0)),
        "note": row.get("Notes","")
    }

st.sidebar.markdown("**Market Returns (%)**")
eq_ret = st.sidebar.number_input("Equity %", value=prefill["eq"], step=1.0, format="%.2f")
debt_ret = st.sidebar.number_input("Debt %", value=prefill["debt"], step=1.0, format="%.2f")
gold_ret = st.sidebar.number_input("Gold %", value=prefill["gold"], step=1.0, format="%.2f")
cash_ret = st.sidebar.number_input("Cash %", value=prefill["cash"], step=1.0, format="%.2f")

st.sidebar.markdown("---")
st.sidebar.subheader("Black Card (optional)")
use_black = st.sidebar.checkbox("Apply Black Card adjustment", value=False)
blk_label = ""
blk_vals = {"eq":0.0,"debt":0.0,"gold":0.0,"cash":0.0}
if use_black:
    blk_id = st.sidebar.selectbox("Black Card", ["None"] + black_df["BlackID"].tolist(), index=0)
    if blk_id != "None":
        rowb = black_df[black_df["BlackID"]==blk_id].iloc[0].to_dict()
        blk_label = f'{rowb["BlackID"]}: {rowb["Label"]}'
        blk_vals = {
            "eq": float(rowb.get("EqAdj",0.0)),
            "debt": float(rowb.get("DebtAdj",0.0)),
            "gold": float(rowb.get("GoldAdj",0.0)),
            "cash": float(rowb.get("CashAdj",0.0)),
        }

eff_eq = eq_ret + blk_vals["eq"]
eff_debt = debt_ret + blk_vals["debt"]
eff_gold = gold_ret + blk_vals["gold"]
eff_cash = cash_ret + blk_vals["cash"]

st.title("🌀 CycleSense Facilitator Dashboard")
st.caption("Read • React • Rebalance")

colL, colR = st.columns([2, 1.2], gap="large")

with colL:
    st.subheader(f"Round {st.session_state.round}: {phase} {' ' if card_id=='Manual' else card_id}")
    if prefill["note"]:
        st.info(prefill["note"])
    if use_black and blk_label:
        st.warning(f"Black Card Applied: {blk_label} (adj in %pts)")

    st.markdown("### Team Inputs")
    rows = []
    for team in st.session_state.teams:
        with st.expander(f"{team} — Current NAV: {st.session_state.nav[team]:.2f}", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            eq_pct = c1.slider("Equity %", 0, 100, 25, key=f"eq_{team}")
            debt_pct = c2.slider("Debt %", 0, 100, 25, key=f"debt_{team}")
            gold_pct = c3.slider("Gold %", 0, 100, 25, key=f"gold_{team}")
            cash_pct = c4.slider("Cash %", 0, 100, 25, key=f"cash_{team}")
            total = eq_pct + debt_pct + gold_pct + cash_pct
            if total != 100:
                st.caption(f"Allocation total = {total}%")

            c5, c6 = st.columns(2)
            pitch = c5.number_input("Pitch Score (₹)", min_value=0.0, max_value=5.0, value=0.0, step=0.5, key=f"pitch_{team}")
            emotion = c6.number_input("Emotion Score (₹)", min_value=0.0, max_value=5.0, value=0.0, step=0.5, key=f"emotion_{team}")

            port_ret = (
                (eq_pct * eff_eq) +
                (debt_pct * eff_debt) +
                (gold_pct * eff_gold) +
                (cash_pct * eff_cash)
            ) / 100.0

            rows.append({
                "Team": team,
                "Equity%": eq_pct, "Debt%": debt_pct, "Gold%": gold_pct, "Cash%": cash_pct,
                "Eff_Eq%": eff_eq, "Eff_Debt%": eff_debt, "Eff_Gold%": eff_gold, "Eff_Cash%": eff_cash,
                "Portfolio Return %": port_ret,
                "Pitch ₹": pitch, "Emotion ₹": emotion,
                "Old NAV": st.session_state.nav[team],
            })

    df_round = pd.DataFrame(rows)
    df_round["New NAV"] = (df_round["Old NAV"] * (1 + df_round["Portfolio Return %"]/100.0)) + df_round["Pitch ₹"] + df_round["Emotion ₹"]
    st.markdown("### Round Results (Preview)")
    st.dataframe(df_round[["Team","Portfolio Return %","Pitch ₹","Emotion ₹","Old NAV","New NAV"]], use_container_width=True)

    cA, cB, cC = st.columns(3)
    if cA.button("✅ Confirm Round & Update NAV"):
        round_meta = {
            "round": st.session_state.round,
            "phase": phase,
            "card": card_id,
            "returns": {"eq":eq_ret,"debt":debt_ret,"gold":gold_ret,"cash":cash_ret},
            "black": blk_label if (use_black and blk_label) else None
        }
        hist_rows = df_round.to_dict(orient="records")
        st.session_state.history.append({"meta": round_meta, "rows": hist_rows})
        for r in hist_rows:
            st.session_state.nav[r["Team"]] = float(r["New NAV"])
        st.session_state.round += 1
        st.success("Round saved and NAVs updated! Scroll to Leaderboard.")

    if cB.button("➕ Add Team"):
        new_name = f"Team {chr(65+len(st.session_state.teams))}"
        st.session_state.teams.append(new_name)
        st.session_state.nav[new_name] = 10.0
        st.experimental_rerun()

    if cC.button("🔄 Reset Session"):
        st.session_state.teams = ["Team A", "Team B", "Team C"]
        st.session_state.nav = {t: 10.0 for t in st.session_state.teams}
        st.session_state.history = []
        st.session_state.round = 1
        st.experimental_rerun()

with colR:
    st.subheader("Leaderboard")
    nav_df = pd.DataFrame({
        "Team": list(st.session_state.nav.keys()),
        "NAV": list(st.session_state.nav.values())
    }).sort_values("NAV", ascending=False)
    st.dataframe(nav_df, use_container_width=True, height=300)
    fig = px.bar(nav_df, x="Team", y="NAV", text="NAV")
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(yaxis_title="NAV", xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Round Log")
    if not st.session_state.history:
        st.caption("No rounds saved yet.")
    else:
        for h in reversed(st.session_state.history[-6:]):
            meta = h["meta"]
            st.markdown(f"**Round {meta['round']}** — {meta['phase']} {meta['card']}")
            if meta["black"]:
                st.caption(f"Black Card: {meta['black']}")
            mini = pd.DataFrame(h["rows"])[["Team","Portfolio Return %","Pitch ₹","Emotion ₹","Old NAV","New NAV"]]
            st.dataframe(mini, use_container_width=True, height=160)

st.markdown("---")
with st.expander("Help", expanded=False):
    st.markdown(
        "- NAV formula: New NAV = (Old NAV * (1 + Portfolio Return%)) + Pitch ₹ + Emotion ₹\n"
        "- Black cards apply additive adjustments (percentage points) to the returns for this round.\n"
        "- Extend card prefills in cards_min.csv and black cards in black_cards.csv.\n"
        "- Starting NAV is 10 per team."
    )
