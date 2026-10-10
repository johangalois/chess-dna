
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed"

GAMES_FILE = DATA_DIR / "games.csv"


def load_games():
    games = pd.read_csv(GAMES_FILE)

    games["date"] = pd.to_datetime(
        games["date"],
        format="%Y.%m.%d",
        errors="coerce",
    )

    games["actual_score"] = pd.to_numeric(
        games["actual_score"], errors="coerce"
    )
    games["expected_score"] = pd.to_numeric(
        games["expected_score"], errors="coerce"
    )
    games["own_rating"] = pd.to_numeric(
        games["own_rating"], errors="coerce"
    )

    games["outcome"] = games["actual_score"].map({
        1.0: "Win",
        0.5: "Draw",
        0.0: "Loss",
    })

    return games


def build_color_stats(games):
    stats = (
        games.groupby("color")
        .agg(
            games=("game_id", "count"),
            score_rate=("actual_score", "mean"),
            expected_score=("expected_score", "mean"),
            avg_own_rating=("own_rating", "mean"),
            avg_opponent_rating=("opponent_rating", "mean"),
        )
        .reset_index()
    )

    stats["performance_gap"] = (
        stats["score_rate"] - stats["expected_score"]
    )

    return stats


def build_opening_stats(games, minimum_games=10):
    stats = (
        games.dropna(subset=["opening"])
        .groupby(["opening", "eco"], dropna=False)
        .agg(
            games=("game_id", "count"),
            score_rate=("actual_score", "mean"),
            expected_score=("expected_score", "mean"),
            avg_own_rating=("own_rating", "mean"),
            avg_opponent_rating=("opponent_rating", "mean"),
        )
        .reset_index()
    )

    stats["performance_gap"] = (
        stats["score_rate"] - stats["expected_score"]
    )

    stats = stats[stats["games"] >= minimum_games]

    return stats.sort_values(
        ["performance_gap", "games"],
        ascending=[False, False],
    )


def build_rating_trend(games):
    valid = games.dropna(subset=["date", "own_rating"]).copy()

    # El rating de una partida no siempre es el rating de cierre del día.
    # Usamos el último registro cronológico disponible de cada día.
    valid = valid.sort_values(["date", "game_id"])

    trend = (
        valid.groupby("date")
        .agg(
            games=("game_id", "count"),
            rating=("own_rating", "last"),
            score_rate=("actual_score", "mean"),
        )
        .reset_index()
    )

    trend["rolling_rating_30_games"] = (
        trend["rating"].rolling(30, min_periods=5).mean()
    )

    return trend


def build_opponent_stats(games):
    valid = games.dropna(subset=["opponent_rating"]).copy()

    valid["opponent_rating_band"] = pd.cut(
        valid["opponent_rating"],
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

    stats = (
        valid.groupby("opponent_rating_band", observed=True)
        .agg(
            games=("game_id", "count"),
            score_rate=("actual_score", "mean"),
            expected_score=("expected_score", "mean"),
        )
        .reset_index()
    )

    stats["performance_gap"] = (
        stats["score_rate"] - stats["expected_score"]
    )

    return stats


def print_overall_summary(games):
    valid = games.dropna(subset=["actual_score", "expected_score"])

    wins = int((valid["actual_score"] == 1.0).sum())
    draws = int((valid["actual_score"] == 0.5).sum())
    losses = int((valid["actual_score"] == 0.0).sum())

    score_rate = valid["actual_score"].mean()
    expected = valid["expected_score"].mean()
    gap = score_rate - expected

    print("\n" + "=" * 60)
    print("CHESS DNA - RESUMEN GENERAL")
    print("=" * 60)
    print(f"Partidas: {len(games):,}")
    print(f"Victorias: {wins:,}")
    print(f"Tablas: {draws:,}")
    print(f"Derrotas: {losses:,}")
    print(f"Puntuación real: {score_rate:.1%}")
    print(f"Puntuación esperada por Elo: {expected:.1%}")
    print(f"Diferencia real vs. esperada: {gap:+.1%}")
    print(f"Elo propio promedio: {games['own_rating'].mean():.1f}")
    print(
        f"Rating registrado más reciente: "
        f"{games.sort_values('date')['own_rating'].iloc[-1]:.0f}"
    )


def main():
    if not GAMES_FILE.exists():
        raise FileNotFoundError(
            f"No existe {GAMES_FILE}. Ejecuta primero transform.py."
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    games = load_games()

    color_stats = build_color_stats(games)
    opening_stats = build_opening_stats(games)
    rating_trend = build_rating_trend(games)
    opponent_stats = build_opponent_stats(games)

    color_stats.to_csv(DATA_DIR / "color_stats.csv", index=False)
    opening_stats.to_csv(DATA_DIR / "opening_stats.csv", index=False)
    rating_trend.to_csv(DATA_DIR / "rating_trend.csv", index=False)
    opponent_stats.to_csv(DATA_DIR / "opponent_stats.csv", index=False)

    print_overall_summary(games)

    print("\n--- Rendimiento por color ---")
    print(color_stats.round(3).to_string(index=False))

    print("\n--- Mejores aperturas (mínimo 10 partidas) ---")
    if opening_stats.empty:
        print("No hay aperturas con suficientes partidas.")
    else:
        print(
            opening_stats[
                ["opening", "eco", "games", "score_rate", "performance_gap"]
            ].head(10).round(3).to_string(index=False)
        )

    print("\n--- Rendimiento por Elo rival ---")
    print(opponent_stats.round(3).to_string(index=False))

    print("\nArchivos analíticos generados:")
    print("- color_stats.csv")
    print("- opening_stats.csv")
    print("- rating_trend.csv")
    print("- opponent_stats.csv")


if __name__ == "__main__":
    main()
