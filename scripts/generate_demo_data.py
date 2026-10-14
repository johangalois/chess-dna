from pathlib import Path

import numpy as np
import pandas as pd

# Reproducible synthetic data. No real Lichess games are used.
rng = np.random.default_rng(42)
n_games = 600

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "demo" / "games.csv"

start = pd.Timestamp("2024-01-01")
end = pd.Timestamp("2026-10-10")
days = (end - start).days

dates = start + pd.to_timedelta(
    rng.integers(0, days + 1, size=n_games), unit="D"
)
dates = pd.to_datetime(dates).strftime("%Y.%m.%d")

colors = rng.choice(["White", "Black"], size=n_games)
own_rating = np.clip(
    1950 + np.linspace(0, 180, n_games) + rng.normal(0, 45, n_games),
    1750,
    2350,
).round().astype(int)

opponent_rating = np.clip(
    own_rating + rng.normal(0, 100, n_games), 1600, 2500
).round().astype(int)

rating_diff = own_rating - opponent_rating
expected_score = 1 / (1 + 10 ** (-rating_diff / 400))

# Synthetic outcomes with a small performance variation.
actual_score = np.array([
    rng.choice([1.0, 0.5, 0.0], p=[
        min(0.75, max(0.15, e * 0.85 + 0.10)),
        0.12,
        1 - min(0.75, max(0.15, e * 0.85 + 0.10)) - 0.12,
    ])
    for e in expected_score
])

openings = [
    ("Italian Game", "C50"),
    ("Sicilian Defense", "B20"),
    ("Queen's Gambit", "D06"),
    ("French Defense", "C00"),
    ("Ruy Lopez", "C60"),
    ("King's Indian Defense", "E60"),
    ("Caro-Kann Defense", "B10"),
    ("English Opening", "A10"),
]

opening_indices = rng.choice(len(openings), size=n_games)
selected_openings = [openings[i] for i in opening_indices]

df = pd.DataFrame({
    "game_id": [f"DEMO-{i:04d}" for i in range(1, n_games + 1)],
    "date": dates,
    "color": colors,
    "actual_score": actual_score,
    "expected_score": expected_score.round(4),
    "own_rating": own_rating,
    "opponent_rating": opponent_rating,
    "opening": [item[0] for item in selected_openings],
    "eco": [item[1] for item in selected_openings],
})

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT, index=False)

print("Synthetic demo dataset created.")
print(f"Rows: {len(df)}")
print(f"Output: {OUTPUT}")
print("This dataset contains generated data, not real games.")
