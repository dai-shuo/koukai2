from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

try:
    from opencc import OpenCC
except Exception:  # pragma: no cover - optional runtime dependency fallback
    OpenCC = None

ROOT = Path(__file__).resolve().parent
DEFAULT_CSV_PATH = ROOT / 'pat-map.csv'
_T2S = OpenCC('t2s') if OpenCC is not None else None
_S2T = OpenCC('s2t') if OpenCC is not None else None


def normalize_game_bytes(raw: str) -> str:
    parts = raw.strip().upper().replace('0X', '').replace('-', ' ').split()
    if len(parts) == 1 and len(parts[0]) == 4:
        parts = [parts[0][:2], parts[0][2:]]
    if len(parts) != 2 or any(len(p) != 2 for p in parts):
        raise ValueError(f'invalid game-byte string: {raw!r}')
    return f'{parts[0]} {parts[1]}'


def split_game_string(raw: str) -> list[str]:
    text = raw.strip().upper().replace('0X', '').replace('-', ' ')
    parts = text.split()
    if not parts:
        raise ValueError('empty game string')
    # Allow common forms:
    # - "92 78"
    # - "9278"
    # - "99 FB A9 94"
    # - "99FBA994"
    if all(len(part) == 2 for part in parts):
        if len(parts) % 2 != 0:
            raise ValueError(f'odd number of bytes in game string: {raw!r}')
        return [f'{parts[i]} {parts[i+1]}' for i in range(0, len(parts), 2)]
    if len(parts) == 1 and len(parts[0]) % 4 == 0:
        token = parts[0]
        return [f'{token[i:i+2]} {token[i+2:i+4]}' for i in range(0, len(token), 4)]
    raise ValueError(f'invalid game string: {raw!r}')


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


def game_to_text(raw: str, table: dict[str, str]) -> str:
    return ''.join(table.get(token, '') for token in split_game_string(raw))


def text_to_game(token: str, table: dict[str, list[str]]) -> str:
    codes = table.get(token, [])
    return ' '.join(codes)


def cmd_translate(args: argparse.Namespace) -> int:
    rows = load_rows(Path(args.csv).expanduser().resolve())
    by_g_t, by_g_s, trad_to_games, simp_to_games, trad_u_to_games, simp_u_to_games = build_indexes(rows)
    mode = args.mode.lower()

    if mode == 'g2t':
        print(game_to_text(args.value, by_g_t))
        return 0
    if mode == 'g2s':
        print(game_to_text(args.value, by_g_s))
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
    if mode == 't2s':
        if _T2S is None:
            raise RuntimeError('OpenCC is not available for t2s conversion')
        print(_T2S.convert(args.value))
        return 0
    if mode == 's2t':
        if _S2T is None:
            raise RuntimeError('OpenCC is not available for s2t conversion')
        print(_S2T.convert(args.value))
        return 0
    raise ValueError(f'unsupported mode: {args.mode}')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Translate between game encoding, Traditional Chinese, and Simplified Chinese using pat-map.csv')
    parser.add_argument('mode', help='g2t, g2s, t2g, s2g, t2s, or s2t')
    parser.add_argument('value', help='input value, such as "92 78", "龜", "龟", or a multi-code game string')
    parser.add_argument('--csv', default=str(DEFAULT_CSV_PATH), help='path to pat-map.csv')
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(cmd_translate(args))


if __name__ == '__main__':
    main()
