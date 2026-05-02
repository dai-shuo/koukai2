from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_CSV_PATH = ROOT / 'pat-map.csv'


def normalize_game_bytes(raw: str) -> str:
    parts = raw.strip().upper().replace('0X', '').replace('-', ' ').split()
    if len(parts) == 1 and len(parts[0]) == 4:
        parts = [parts[0][:2], parts[0][2:]]
    if len(parts) != 2 or any(len(p) != 2 for p in parts):
        raise ValueError(f'invalid game-byte string: {raw!r}')
    return f'{parts[0]} {parts[1]}'


def parse_unicode_token(raw: str) -> str:
    text = raw.strip()
    if text.upper().startswith('U+'):
        return chr(int(text[2:], 16))
    if len(text) == 1:
        return text
    raise ValueError(f'invalid Unicode token: {raw!r}')


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def build_indexes(rows: list[dict[str, str]]):
    by_game_to_trad: dict[str, str] = {}
    by_game_to_simp: dict[str, str] = {}
    trad_to_games: dict[str, list[str]] = defaultdict(list)
    simp_to_games: dict[str, list[str]] = defaultdict(list)
    trad_u_to_games: dict[str, list[str]] = defaultdict(list)
    simp_u_to_games: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        byte = row['byte'].upper()
        trad = row['char']
        trad_u = row['unicode']
        simp = row['chs_char']
        simp_u = row['chs_unicode']
        by_game_to_trad[byte] = trad
        by_game_to_simp[byte] = simp
        if trad:
            trad_to_games[trad].append(byte)
        if simp:
            simp_to_games[simp].append(byte)
        if trad_u:
            trad_u_to_games[trad_u].append(byte)
        if simp_u:
            simp_u_to_games[simp_u].append(byte)
    return by_game_to_trad, by_game_to_simp, trad_to_games, simp_to_games, trad_u_to_games, simp_u_to_games


def cmd_translate(args: argparse.Namespace) -> int:
    rows = load_rows(Path(args.csv).expanduser().resolve())
    by_g_t, by_g_s, trad_to_games, simp_to_games, trad_u_to_games, simp_u_to_games = build_indexes(rows)
    mode = args.mode.lower()
    if mode == 'g2t':
        byte = normalize_game_bytes(args.value)
        print(by_g_t.get(byte, ''))
        return 0
    if mode == 'g2s':
        byte = normalize_game_bytes(args.value)
        print(by_g_s.get(byte, ''))
        return 0
    if mode == 't2g':
        token = parse_unicode_token(args.value)
        codes = trad_to_games.get(token, []) or trad_u_to_games.get(f'U+{ord(token):04X}', [])
        print(' '.join(codes))
        return 0
    if mode == 's2g':
        token = parse_unicode_token(args.value)
        codes = simp_to_games.get(token, []) or simp_u_to_games.get(f'U+{ord(token):04X}', [])
        print(' '.join(codes))
        return 0
    raise ValueError(f'unsupported mode: {args.mode}')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Translate between game encoding and Traditional/Simplified Chinese using pat-map.csv')
    parser.add_argument('mode', help='g2t, g2s, t2g, or s2g')
    parser.add_argument('value', help='input value, such as "92 78", "龜", or "龟"')
    parser.add_argument('--csv', default=str(DEFAULT_CSV_PATH), help='path to pat-map.csv')
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(cmd_translate(args))


if __name__ == '__main__':
    main()
