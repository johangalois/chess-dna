
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "processed"
DEMO_DIR = ROOT / "data" / "demo"

st.set_page_config(
    page_title="Chess DNA",
    page_icon="♟️",
    layout="wide",
)

st.title("♟️ Chess DNA")
st.caption("What chess games reveal about playing style and performance")


# --------------------------------------------------
# 2. LOAD DATA
# --------------------------------------------------
# Priority:
# 1. Personal dataset (available locally, ignored by Git)
# 2. Synthetic demo dataset (safe to publish)

personal_file = DATA_DIR / "games.csv"
demo_file = DEMO_DIR / "games.csv"

if personal_file.exists():
    df = pd.read_csv(personal_file)
    demo_mode = False

    st.info(
        "Personal mode: using your own chess games. "
        "Your personal dataset is stored locally."
    )

elif demo_file.exists():
    df = pd.read_csv(demo_file)
    demo_mode = True

    st.info(
        "Demo mode: using synthetic chess data. "
        "These results do not represent a real player's performance."
    )

else:
    st.error(
        "No dataset found. Place your personal games in "
        "data/processed/games.csv or generate the demo dataset."
    )
    st.stop()


# --------------------------------------------------
# 3. VALIDATE AND PREPARE DATA
# --------------------------------------------------

required_columns = [
    "game_id",
    "date",
    "color",
    "actual_score",
    "expected_score",
    "own_rating",
    "opponent_rating",
    "opening",
    "eco",
]

missing_columns = [
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:
    st.error(
        "The dataset is missing required columns: "
        + ", ".join(missing_columns)
    )
    st.stop()

df["date"] = pd.to_datetime(
    df["date"].astype(str).str.replace(".", "-", regex=False),
    errors="coerce",
)

numeric_columns = [
    "actual_score",
    "expected_score",
    "own_rating",
    "opponent_rating",
]

for column in numeric_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")

df["color"] = df["color"].astype(str).str.lower()

df["outcome"] = df["actual_score"].map({
    1.0: "Win",
    0.5: "Draw",
    0.0: "Loss",
})

df = df.dropna(subset=["date", "actual_score", "expected_score"])

if df.empty:
    st.error("The dataset contains no valid games to analyze.")
    st.stop()

min_date = df["date"].min().date()
max_date = df["date"].max().date()


# --------------------------------------------------
# 4. SIDEBAR FILTERS
# --------------------------------------------------

st.sidebar.header("Filters")

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

available_colors = [
    color for color in ["white", "black"]
    if color in df["color"].unique()
]

colors = st.sidebar.multiselect(
    "Color",
    options=available_colors,
    default=available_colors,
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


# --------------------------------------------------
# 5. KEY PERFORMANCE INDICATORS
# --------------------------------------------------

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

if pd.notna(avg_rating):
    c5.metric("Average rating", f"{avg_rating:.0f}")
else:
    c5.metric("Average rating", "N/A")

st.divider()


# --------------------------------------------------
# 6. RESULTS AND SCORE BY COLOR
# --------------------------------------------------

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
        title="Distribution of results",
    )

    st.plotly_chart(fig, width="stretch")

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
        title="Actual vs. expected score",
    )

    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")

st.divider()


# --------------------------------------------------
# 7. RATING HISTORY
# --------------------------------------------------

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
        hover_data=[
            "opponent_rating",
            "outcome",
            "opening",
        ],
        labels={
            "date": "Date",
            "own_rating": "Rating",
            "color": "Color",
        },
        opacity=0.65,
        title="Rating across games",
    )

    fig.update_traces(marker={"size": 6})
    st.plotly_chart(fig, width="stretch")
else:
    st.info("No rating history is available for these filters.")

st.divider()


# --------------------------------------------------
# 8. PERFORMANCE BY OPPONENT RATING
# --------------------------------------------------

st.subheader("Performance by opponent rating")

rating_df = filtered.dropna(
    subset=["opponent_rating"]
).copy()

if not rating_df.empty:
    rating_df["rating_band"] = pd.cut(
        rating_df["opponent_rating"],
        bins=[0, 1800, 2000, 2200, 2400, float("inf")],
        labels=[
            "<1800",
            "1800–1999",
            "2000–2199",
            "2200–2399",
            "2400+",
        ],
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
        title="Actual vs. expected score by opponent strength",
    )

    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")
else:
    st.info("No opponent rating data is available for these filters.")

st.divider()


# --------------------------------------------------
# 9. OPENING PERFORMANCE
# --------------------------------------------------

st.subheader("Opening performance")

opening_data = filtered.dropna(
    subset=["opening"]
).copy()

if not opening_data.empty:
    opening_stats = (
        opening_data.groupby(
            ["opening", "eco"],
            dropna=False,
        )
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

    minimum_available = min(5, int(opening_stats["games"].min()))
    maximum_available = max(30, int(opening_stats["games"].max()))

    minimum_games = st.slider(
        "Minimum games per opening",
        min_value=minimum_available,
        max_value=maximum_available,
        value=min(10, maximum_available),
    )

    opening_stats = opening_stats[
        opening_stats["games"] >= minimum_games
    ].sort_values("performance_gap", ascending=False)

    if not opening_stats.empty:
        display_openings = opening_stats.rename(columns={
            "opening": "Opening",
            "eco": "ECO",
            "games": "Games",
            "score": "Actual score",
            "expected": "Expected score",
            "performance_gap": "Performance gap",
        })

        display_openings["Actual score"] = (
            display_openings["Actual score"].map("{:.1%}".format)
        )
        display_openings["Expected score"] = (
            display_openings["Expected score"].map("{:.1%}".format)
        )
        display_openings["Performance gap"] = (
            display_openings["Performance gap"].map("{:+.1%}".format)
        )

        st.dataframe(
            display_openings,
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No openings meet the selected minimum game count.")
else:
    st.info("No opening data is available for these filters.")


# --------------------------------------------------
# 10. FOOTER
# --------------------------------------------------

st.divider()

if demo_mode:
    st.caption(
        "Chess DNA portfolio demo | Synthetic data only | "
        "No real player game records are used in this view."
    )
else:
    st.caption(
        "Chess DNA | Personal analysis | "
        "Rating and performance metrics are descriptive, "
        "not a prediction of future results."
    )
