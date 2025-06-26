import streamlit as st
import pandas as pd
from pulp import LpProblem, LpVariable, lpSum, LpMaximize, LpBinary

st.set_page_config(page_title="Fantasy Draft Optimizer", layout="wide")

st.title("🏈 Fantasy Football Draft Optimizer")

uploaded_available = st.file_uploader("Upload Available Players CSV", type="csv")
uploaded_drafted = st.file_uploader("Upload Drafted Players CSV", type="csv")

if uploaded_available and uploaded_drafted:
    available_df = pd.read_csv(uploaded_available)
    drafted_df = pd.read_csv(uploaded_drafted)

    # Clean data
    available_df = available_df.dropna(subset=["Player"])
    drafted_df = drafted_df.dropna(subset=["Player"])

    # Ensure correct data types
    available_df["ProjectedPts"] = pd.to_numeric(available_df["ProjectedPts"], errors="coerce")
    available_df["Price"] = pd.to_numeric(available_df["Price"], errors="coerce")
    available_df.dropna(subset=["ProjectedPts", "Price"], inplace=True)

    # Remove duplicates: exclude any player in both
    available_df = available_df[~available_df["Player"].isin(drafted_df["Player"])]

    # Add 'Locked' column to drafted players
    drafted_df["Locked"] = True
    available_df["Locked"] = False

    # Combine
    full_df = pd.concat([drafted_df, available_df], ignore_index=True)

    # Optimization
    prob = LpProblem("FantasyOptimizer", LpMaximize)
    selected_vars = LpVariable.dicts("Select", full_df.index, cat=LpBinary)

    # Constraints
    budget = 192 - drafted_df["Price"].sum()
    prob += lpSum(full_df.loc[i, "Price"] * selected_vars[i] for i in full_df.index) <= budget

    # Position constraints
    required = {
        "QB": 2,
        "RB": 2,
        "WR": 3,
        "TE": 1,
        "FLEX": 2
    }

    def position_filter(pos):
        return full_df["Position"] == pos

    # Hard requirements
    for pos, count in required.items():
        if pos != "FLEX":
            prob += lpSum(selected_vars[i] for i in full_df.index if full_df.loc[i, "Position"] == pos) + \
                    sum(drafted_df["Position"] == pos) == count

    # FLEX constraint (can be RB, WR, TE)
    flex_eligible = full_df["Position"].isin(["RB", "WR", "TE"])
    prob += lpSum(selected_vars[i] for i in full_df.index if flex_eligible[i]) + \
            sum(drafted_df["Position"].isin(["RB", "WR", "TE"])) >= required["FLEX"]

    # Enforce locked (drafted) players
    for i in full_df.index:
        if full_df.loc[i, "Locked"]:
            prob += selected_vars[i] == 1

    # Maximize points
    prob += lpSum(full_df.loc[i, "ProjectedPts"] * selected_vars[i] for i in full_df.index)

    prob.solve()

    selected_df = full_df[[selected_vars[i].varValue == 1 for i in full_df.index]]
    selected_df = selected_df.reset_index(drop=True)

    st.subheader("✅ Optimal Lineup")
    st.dataframe(selected_df)

    st.markdown(f"""
    - 🏈 **Total Points:** {selected_df["ProjectedPts"].sum():.2f}  
    - 💰 **Total Cost:** {selected_df["Price"].sum():.2f}  
    - 👥 **Total Players:** {len(selected_df)}  
    """)
