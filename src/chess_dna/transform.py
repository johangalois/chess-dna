
from pathlib import Path

import chess
import chess.pgn
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "games.pgn"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

GAMES_OUTPUT = OUTPUT_DIR / "games.csv"
MOVES_OUTPUT = OUTPUT_DIR / "moves.csv"

USERNAME = "johangalois"


def to_int(value):
    """Convierte un valor a entero; devuelve None si no es válido."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def expected_score(own_rating, opponent_rating):
    """Calcula el resultado esperado según la diferencia de Elo."""
    if own_rating is None or opponent_rating is None:
        return None

    return 1 / (1 + 10 ** ((opponent_rating - own_rating) / 400))


def parse_game(game):
    """Transforma una partida PGN en un registro de partida y sus movimientos."""
    headers = game.headers

    white = headers.get("White", "")
    black = headers.get("Black", "")
    result = headers.get("Result", "*")

    if white.lower() == USERNAME.lower():
        color = "white"
        own_rating = to_int(headers.get("WhiteElo"))
        opponent_rating = to_int(headers.get("BlackElo"))
        white_result = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}.get(result)
    elif black.lower() == USERNAME.lower():
        color = "black"
        own_rating = to_int(headers.get("BlackElo"))
        opponent_rating = to_int(headers.get("WhiteElo"))
        white_result = {"1-0": 0.0, "0-1": 1.0, "1/2-1/2": 0.5}.get(result)
    else:
        raise ValueError(
            f"La partida no contiene al usuario {USERNAME}: {white} vs {black}"
        )

    game_id = headers.get("GameId") or headers.get("Site", "").rstrip("/").split("/")[-1]

    actual = white_result
    expected = expected_score(own_rating, opponent_rating)

    # Cada nodo de la línea principal representa un movimiento realizado.
    move_records = []
    ply = 0

    for node in game.mainline():
        ply += 1
        move_color = "white" if ply % 2 == 1 else "black"

        try:
            clock_seconds = node.clock()
        except (ValueError, TypeError):
            clock_seconds = None

        move_records.append({
            "game_id": game_id,
            "ply": ply,
            "move_number": (ply + 1) // 2,
            "color": move_color,
            "san": node.san(),
            "uci": node.move.uci(),
            "clock_seconds": clock_seconds,
        })

    game_record = {
        "game_id": game_id,
        "date": headers.get("UTCDate", headers.get("Date")),
        "white": white,
        "black": black,
        "color": color,
        "result": result,
        "actual_score": actual,
        "own_rating": own_rating,
        "opponent_rating": opponent_rating,
        "rating_diff": (
            own_rating - opponent_rating
            if own_rating is not None and opponent_rating is not None
            else None
        ),
        "expected_score": expected,
        "performance_gap": (
            actual - expected
            if actual is not None and expected is not None
            else None
        ),
        "time_control": headers.get("TimeControl"),
        "opening": headers.get("Opening"),
        "eco": headers.get("ECO"),
        "moves_count": ply,
        "termination": headers.get("Termination"),
    }

    return game_record, move_records


def transform_games():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"No existe el archivo PGN: {INPUT_FILE}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    games = []
    moves = []
    parse_errors = 0

    print("=" * 60)
    print("CHESS DNA - TRANSFORMACIÓN")
    print("=" * 60)
    print(f"Entrada: {INPUT_FILE}")

    with INPUT_FILE.open("r", encoding="utf-8") as pgn_file:
        while True:
            game = chess.pgn.read_game(pgn_file)

            if game is None:
                break

            if game.errors:
                parse_errors += 1
                print(
                    f"Advertencia: errores al leer la partida "
                    f"{game.headers.get('GameId', 'desconocida')}"
                )

            try:
                game_record, move_records = parse_game(game)
                games.append(game_record)
                moves.extend(move_records)
            except ValueError as error:
                parse_errors += 1
                print(f"Partida omitida: {error}")

    games_df = pd.DataFrame(games)
    moves_df = pd.DataFrame(moves)

    if games_df.empty:
        raise ValueError("No se pudo transformar ninguna partida.")

    # Asegura que cada ID represente una sola partida.
    duplicate_count = int(games_df["game_id"].duplicated().sum())

    if duplicate_count:
        raise ValueError(
            f"Se encontraron {duplicate_count} partidas duplicadas."
        )

    games_df.to_csv(GAMES_OUTPUT, index=False, encoding="utf-8")
    moves_df.to_csv(MOVES_OUTPUT, index=False, encoding="utf-8")

    print()
    print("=" * 60)
    print("TRANSFORMACIÓN TERMINADA")
    print("=" * 60)
    print(f"Partidas procesadas: {len(games_df):,}")
    print(f"Movimientos procesados: {len(moves_df):,}")
    print(f"Errores de lectura o partidas omitidas: {parse_errors}")
    print(f"IDs de partida duplicados: {duplicate_count}")
    print(f"CSV de partidas: {GAMES_OUTPUT}")
    print(f"CSV de movimientos: {MOVES_OUTPUT}")

    print("\nColumnas de games.csv:")
    print(", ".join(games_df.columns))

    print("\nColumnas de moves.csv:")
    print(", ".join(moves_df.columns))

    return games_df, moves_df


if __name__ == "__main__":
    transform_games()
