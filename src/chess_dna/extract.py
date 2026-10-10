
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import re
import time

import requests

USERNAME = "johangalois"
MAX_GAMES = 5_000
BATCH_SIZE = 500
START_DATE = "2024-01-01"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_FILE = RAW_DIR / "games.pgn"
API_URL = f"https://lichess.org/api/games/user/{USERNAME}"


def parse_game_metadata(game_text):
    site = re.search(r'^\[Site "([^"]+)"\]', game_text, re.MULTILINE)
    utc_date = re.search(r'^\[UTCDate "([^"]+)"\]', game_text, re.MULTILINE)
    utc_time = re.search(r'^\[UTCTime "([^"]+)"\]', game_text, re.MULTILINE)

    if site:
        game_id = site.group(1).rstrip("/").split("/")[-1]
    else:
        game_id = sha256(game_text.encode("utf-8")).hexdigest()

    timestamp = None

    if utc_date and utc_time:
        try:
            game_datetime = datetime.strptime(
                f"{utc_date.group(1)} {utc_time.group(1)}",
                "%Y.%m.%d %H:%M:%S",
            ).replace(tzinfo=timezone.utc)

            timestamp = int(game_datetime.timestamp() * 1000)
        except ValueError:
            pass

    return game_id, timestamp


def extract_games() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    since = int(
        datetime.strptime(START_DATE, "%Y-%m-%d")
        .replace(tzinfo=timezone.utc)
        .timestamp() * 1000
    )

    until = None
    all_games = []
    seen_ids = set()
    batch_number = 0

    headers = {
        "Accept": "application/x-chess-pgn",
        "User-Agent": "ChessDNA/0.1 personal analytics project",
    }

    print("=" * 60)
    print("CHESS DNA - EXTRACCIÓN")
    print("=" * 60)
    print(f"Usuario: {USERNAME}")
    print(f"Desde: {START_DATE}")
    print("Ritmo: rapid")
    print(f"Máximo: {MAX_GAMES:,} partidas")
    print(f"Tamaño de lote solicitado: {BATCH_SIZE}")
    print()

    with requests.Session() as session:
        session.headers.update(headers)

        while len(all_games) < MAX_GAMES:
            batch_number += 1
            remaining = MAX_GAMES - len(all_games)
            limit = min(BATCH_SIZE, remaining)

            params = {
                "since": since,
                "max": limit,
                "perfType": "rapid",
                "clocks": "true",
                "opening": "true",
                "sort": "dateDesc",
            }

            if until is not None:
                params["until"] = until

            print(
                f"Lote {batch_number}: solicitando hasta {limit} "
                f"partidas únicas..."
            )

            response = session.get(
                API_URL,
                params=params,
                timeout=120,
            )

            print(f"HTTP: {response.status_code}")
            response.raise_for_status()

            content = response.text.strip()

            if not content:
                print("La API no devolvió más partidas.")
                break

            chunks = [
                "[Event " + part
                for part in content.split("[Event ")[1:]
            ]

            if not chunks:
                print("No se pudieron identificar partidas en la respuesta.")
                break

            new_games = []
            timestamps = []

            for game_text in chunks:
                game_id, timestamp = parse_game_metadata(game_text)

                if timestamp is not None:
                    timestamps.append(timestamp)

                if game_id not in seen_ids:
                    seen_ids.add(game_id)
                    new_games.append(game_text)

            if not new_games:
                print("No hay partidas nuevas; detenemos para evitar un bucle.")
                break

            new_games = new_games[:remaining]
            all_games.extend(new_games)

            print(
                f"Partidas nuevas: {len(new_games)} | "
                f"Acumuladas: {len(all_games):,}"
            )

            if len(all_games) >= MAX_GAMES:
                break

            if not timestamps:
                print("No se encontraron fechas UTC para avanzar.")
                break

            oldest_timestamp = min(timestamps)

            if oldest_timestamp <= since:
                print("Se alcanzó la fecha inicial.")
                break

            # La siguiente consulta buscará partidas anteriores.
            next_until = oldest_timestamp - 1

            if until is not None and next_until >= until:
                print("No se pudo avanzar el límite temporal.")
                break

            until = next_until

            if len(chunks) < limit:
                print("La API devolvió menos partidas que las solicitadas.")
                break

            time.sleep(1)

    if not all_games:
        raise ValueError("No se encontraron partidas rapid desde la fecha indicada.")

    OUTPUT_FILE.write_text(
        "\n\n".join(all_games) + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 60)
    print("EXTRACCIÓN TERMINADA")
    print("=" * 60)
    print(f"Partidas guardadas: {len(all_games):,}")
    print(f"Archivo: {OUTPUT_FILE}")
    print(f"Tamaño: {OUTPUT_FILE.stat().st_size:,} bytes")

    return OUTPUT_FILE


if __name__ == "__main__":
    extract_games()


