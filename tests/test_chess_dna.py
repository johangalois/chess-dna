
import io
import sys
import unittest
from pathlib import Path

import chess.pgn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chess_dna.transform import expected_score, parse_game


class TestExpectedScore(unittest.TestCase):
    def test_equal_ratings(self):
        self.assertAlmostEqual(expected_score(2000, 2000), 0.5)

    def test_higher_rated_player_is_favored(self):
        score = expected_score(2000, 1800)
        self.assertGreater(score, 0.5)
        self.assertAlmostEqual(score, 0.7597, places=3)

    def test_lower_rated_player_is_underdog(self):
        self.assertLess(expected_score(1800, 2000), 0.5)

    def test_missing_rating(self):
        self.assertIsNone(expected_score(None, 2000))
        self.assertIsNone(expected_score(2000, None))


class TestGameParsing(unittest.TestCase):
    def parse_sample(self, white, black, result):
        pgn = f"""
[Event "Test game"]
[Site "https://lichess.org/test123"]
[GameId "test123"]
[White "{white}"]
[Black "{black}"]
[Result "{result}"]
[WhiteElo "2000"]
[BlackElo "1800"]
[UTCDate "2026.01.01"]
[TimeControl "600+0"]

1. e4 e5 2. Nf3 Nc6 *
"""
        game = chess.pgn.read_game(io.StringIO(pgn))
        self.assertIsNotNone(game)
        return parse_game(game)

    def test_white_win_from_user_perspective(self):
        record, moves = self.parse_sample(
            "johangalois", "opponent", "1-0"
        )
        self.assertEqual(record["color"], "white")
        self.assertEqual(record["actual_score"], 1.0)
        self.assertEqual(len(moves), 4)

    def test_black_win_from_user_perspective(self):
        record, _ = self.parse_sample(
            "opponent", "johangalois", "0-1"
        )
        self.assertEqual(record["color"], "black")
        self.assertEqual(record["actual_score"], 1.0)
        self.assertEqual(record["own_rating"], 1800)
        self.assertEqual(record["opponent_rating"], 2000)

    def test_draw(self):
        record, _ = self.parse_sample(
            "johangalois", "opponent", "1/2-1/2"
        )
        self.assertEqual(record["actual_score"], 0.5)


if __name__ == "__main__":
    unittest.main()
