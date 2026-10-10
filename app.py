
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "processed"

st.set_page_config(
    page_title="Chess DNA",
    page_icon="♟️",
    layout="wide",
)

st.title("♟️ Chess DNA")
st.caption("What 1,342 games reveal about your chess")

games_file = DATA_DIR / "games.csv"

if not games_file.exists():
    st.error("No se encuentra games.csv. Ejecuta primero transform.py.")
    st.stop()

df = pd.read_csv(games_file)

df["date"] = pd.to_datetime(
    df["date"], format="%Y.%m.%d", errors="coerce"
)
df["actual_score"] = pd.to_numeric(df["actual_score"], errors="coerce")
df["expected_score"] = pd.to_numeric(df["expected_score"], errors="coerce")
df["own_rating"] = pd.to_numeric(df["own_rating"], errors="coerce")
df["opponent_rating"] = pd.to_numeric(
    df["opponent_rating"], errors="coerce"
)

df["outcome"] = df["actual_score"].map({
    1.0: "Win",
    0.5: "Draw",
    0.0: "Loss",
})

min_date = df["date"].min().date()
max_date = df["date"].max().date()

st.sidebar.header("Filters")

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

colors = st.sidebar.multiselect(
    "Color",
    options=["white", "black"],
    default=["white", "black"],
)

if len(date_range) == 2:
    start_date, end_date = date_range
    filtered = df[
        df["date"].dt.date.between(start_date, end_date)
    ].copy()
else:
    filtered = df.copy()

filtered = filtered[filtered["color"].isin(colors)]

if filtered.empty:
    st.warning("No games match the selected filters.")
    st.stop()

n_games = len(filtered)
score = filtered["actual_score"].mean()
expected = filtered["expected_score"].mean()
gap = score - expected
avg_rating = filtered["own_rating"].mean()

wins = int((filtered["actual_score"] == 1).sum())
draws = int((filtered["actual_score"] == 0.5).sum())
losses = int((filtered["actual_score"] == 0).sum())

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Games", f"{n_games:,}")
c2.metric("Score", f"{score:.1%}")
c3.metric("Expected score", f"{expected:.1%}")
c4.metric("Performance gap", f"{gap:+.1%}")
c5.metric("Average rating", f"{avg_rating:.0f}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Results")

    result_df = pd.DataFrame({
        "Outcome": ["Wins", "Draws", "Losses"],
        "Games": [wins, draws, losses],
    })

    fig = px.pie(
        result_df,
        names="Outcome",
        values="Games",
        hole=0.55,
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Score by color")

    color_df = (
        filtered.groupby("color")
        .agg(
            games=("game_id", "count"),
            score=("actual_score", "mean"),
            expected=("expected_score", "mean"),
        )
        .reset_index()
    )

    color_long = color_df.melt(
        id_vars=["color", "games"],
        value_vars=["score", "expected"],
        var_name="metric",
        value_name="value",
    )

    color_long["metric"] = color_long["metric"].map({
        "score": "Actual score",
        "expected": "Expected score",
    })

    fig = px.bar(
        color_long,
        x="color",
        y="value",
        color="metric",
        barmode="group",
        hover_data=["games"],
        labels={
            "color": "Color",
            "value": "Score",
            "metric": "Metric",
        },
    )
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Rating history")

rating_df = filtered.dropna(
    subset=["date", "own_rating"]
).sort_values("date")

if not rating_df.empty:
    fig = px.scatter(
        rating_df,
        x="date",
        y="own_rating",
        color="color",
        hover_data=["opponent_rating", "outcome", "opening"],
        labels={
            "date": "Date",
            "own_rating": "Rating",
            "color": "Color",
        },
        opacity=0.65,
    )
    fig.update_traces(marker={"size": 6})
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Performance by opponent rating")

rating_df = filtered.dropna(
    subset=["opponent_rating"]
).copy()

rating_df["rating_band"] = pd.cut(
    rating_df["opponent_rating"],
    bins=[0, 1800, 2000, 2200, 2400, float("inf")],
    labels=["<1800", "1800–1999", "2000–2199", "2200–2399", "2400+"],
    right=False,
)

opponent_stats = (
    rating_df.groupby("rating_band", observed=True)
    .agg(
        games=("game_id", "count"),
        actual=("actual_score", "mean"),
        expected=("expected_score", "mean"),
    )
    .reset_index()
)

opponent_long = opponent_stats.melt(
    id_vars=["rating_band", "games"],
    value_vars=["actual", "expected"],
    var_name="metric",
    value_name="score",
)

opponent_long["metric"] = opponent_long["metric"].map({
    "actual": "Actual score",
    "expected": "Expected score",
})

fig = px.bar(
    opponent_long,
    x="rating_band",
    y="score",
    color="metric",
    barmode="group",
    hover_data=["games"],
    labels={
        "rating_band": "Opponent rating",
        "score": "Score",
        "metric": "Metric",
    },
)
fig.update_yaxes(tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Opening performance")

opening_stats = (
    filtered.dropna(subset=["opening"])
    .groupby(["opening", "eco"], dropna=False)
    .agg(
        games=("game_id", "count"),
        score=("actual_score", "mean"),
        expected=("expected_score", "mean"),
    )
    .reset_index()
)

opening_stats["performance_gap"] = (
    opening_stats["score"] - opening_stats["expected"]
)

minimum_games = st.slider(
    "Minimum games per opening",
    min_value=5,
    max_value=30,
    value=10,
)

opening_stats = opening_stats[
    opening_stats["games"] >= minimum_games
].sort_values("performance_gap", ascending=False)

if opening_stats.empty:
    st.info("No openings meet the selected minimum.")
else:
    st.dataframe(
        opening_stats[
            [
                "opening",
                "eco",
                "games",
                "score",
                "expected",
                "performance_gap",
            ]
        ].style.format({
            "score": "{:.1%}",
            "expected": "{:.1%}",
            "performance_gap": "{:+.1%}",
        }),
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    "Chess DNA is a personal analytics project. "
    "Performance gap is descriptive and does not measure move accuracy."
)
