from __future__ import annotations

import argparse
import csv
from pathlib import Path
from xml.sax.saxutils import escape

GLYPH_WIDTH = 16
GLYPH_HEIGHT = 14
GLYPH_BYTES = 28
GLYPHS_PER_BLOCK = 18
BLOCK_SIZE = 512
BLOCK_PAYLOAD_BYTES = GLYPHS_PER_BLOCK * GLYPH_BYTES
BLOCK_PADDING_BYTES = BLOCK_SIZE - BLOCK_PAYLOAD_BYTES

CARD_W = 520
CARD_H = 250
PIXEL_SCALE = 8
FRAME_X = 20
FRAME_Y = 28
FRAME_SIZE = 160
TEXT_X = 210

ROOT = Path(__file__).resolve().parent
DEFAULT_CSV_PATH = ROOT / 'pat-map.csv'
DEFAULT_CARDS_DIR = ROOT / 'cards'
DEFAULT_GAME_DIR = ROOT.parent.parent / 'koukai2'


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Generate SVG glyph cards from a PAT map CSV.')
    parser.add_argument('--csv', dest='csv_path', default=str(DEFAULT_CSV_PATH), help='path to pat-map.csv')
    parser.add_argument('--game-dir', default=str(DEFAULT_GAME_DIR), help='directory containing 1.PAT and 2.PAT')
    parser.add_argument('--output-dir', default=str(DEFAULT_CARDS_DIR), help='directory to write SVG cards into')
    return parser


def parse_pat_file(path: Path) -> list[bytes]:
    data = path.read_bytes()
    full_blocks = len(data) // BLOCK_SIZE
    trailing_bytes = len(data) % BLOCK_SIZE
    glyphs: list[bytes] = []
    for block_index in range(full_blocks):
        start = block_index * BLOCK_SIZE
        payload = data[start:start + BLOCK_PAYLOAD_BYTES]
        padding = data[start + BLOCK_PAYLOAD_BYTES:start + BLOCK_SIZE]
        if len(padding) != BLOCK_PADDING_BYTES:
            raise ValueError(f'invalid padding length in block {block_index}')
        for glyph_index in range(GLYPHS_PER_BLOCK):
            glyph_start = glyph_index * GLYPH_BYTES
            glyphs.append(payload[glyph_start:glyph_start + GLYPH_BYTES])
    if trailing_bytes:
        if trailing_bytes % GLYPH_BYTES != 0:
            raise ValueError(f'trailing bytes are not a whole number of glyphs: {trailing_bytes}')
        start = full_blocks * BLOCK_SIZE
        payload = data[start:]
        for glyph_index in range(trailing_bytes // GLYPH_BYTES):
            glyph_start = glyph_index * GLYPH_BYTES
            glyphs.append(payload[glyph_start:glyph_start + GLYPH_BYTES])
    return glyphs


def glyph_to_pixels(glyph: bytes) -> list[list[int]]:
    rows: list[list[int]] = []
    for row_index in range(GLYPH_HEIGHT):
        row_bytes = glyph[row_index * 2:(row_index + 1) * 2]
        value = int.from_bytes(row_bytes, 'big', signed=False)
        row = []
        for bit in range(GLYPH_WIDTH):
            mask = 1 << (GLYPH_WIDTH - 1 - bit)
            row.append(1 if value & mask else 0)
        rows.append(row)
    return rows


def render_card(row: dict[str, str], glyph: bytes) -> str:
    pixels = glyph_to_pixels(glyph)
    bitmap_w = GLYPH_WIDTH * PIXEL_SCALE
    bitmap_h = GLYPH_HEIGHT * PIXEL_SCALE
    bitmap_x = FRAME_X + (FRAME_SIZE - bitmap_w) // 2
    bitmap_y = FRAME_Y + (FRAME_SIZE - bitmap_h) // 2

    parts: list[str] = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}">')
    parts.append('<rect width="100%" height="100%" fill="#fffaf3"/>')
    parts.append('<rect x="1" y="1" width="518" height="248" rx="14" fill="#fffaf3" stroke="#c8b49b" stroke-width="2"/>')
    parts.append('<style>text{font-family:"PingFang SC","Noto Sans CJK SC","Hiragino Sans GB","Songti SC",sans-serif;fill:#221b14}.meta{font-size:22px;font-weight:700}.line{font-size:24px}.byte{font-size:20px;fill:#7a6456}</style>')
    parts.append(f'<rect x="{FRAME_X}" y="{FRAME_Y}" width="{FRAME_SIZE}" height="{FRAME_SIZE}" rx="12" fill="#fbf7ef" stroke="#d8cab8" stroke-width="2"/>')
    for y, line in enumerate(pixels):
        for x, value in enumerate(line):
            if not value:
                continue
            px = bitmap_x + x * PIXEL_SCALE
            py = bitmap_y + y * PIXEL_SCALE
            parts.append(f'<rect x="{px}" y="{py}" width="{PIXEL_SCALE}" height="{PIXEL_SCALE}" fill="#1b1b1b"/>')
    parts.append(f'<text x="{FRAME_X + FRAME_SIZE/2:.0f}" y="{FRAME_Y + FRAME_SIZE + 28}" text-anchor="middle" class="byte">Byte {escape(row["byte"])}</text>')
    parts.append(f'<text x="{TEXT_X}" y="66" class="meta">{escape(row["pat"])} , #{escape(row["index"])}</text>')
    parts.append(f'<text x="{TEXT_X}" y="118" class="line">CHT: {escape(row["char"])}  {escape(row["unicode"])}</text>')
    parts.append(f'<text x="{TEXT_X}" y="170" class="line">CHS: {escape(row["chs_char"])}  {escape(row["chs_unicode"])}</text>')
    parts.append('</svg>')
    return ''.join(parts)


def main() -> None:
    args = build_parser().parse_args()
    csv_path = Path(args.csv_path).expanduser().resolve()
    game_dir = Path(args.game_dir).expanduser().resolve()
    cards_dir = Path(args.output_dir).expanduser().resolve()
    cards_dir.mkdir(parents=True, exist_ok=True)
    pat_paths = {
        '1.PAT': game_dir / '1.PAT',
        '2.PAT': game_dir / '2.PAT',
    }
    glyph_cache = {pat_name: parse_pat_file(path) for pat_name, path in pat_paths.items()}
    with csv_path.open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        pat_name = row['pat']
        index1 = int(row['index'])
        glyph = glyph_cache[pat_name][index1 - 1]
        svg = render_card(row, glyph)
        prefix = '1' if pat_name == '1.PAT' else '2'
        file_name = f'{prefix}-{index1:04d}.svg'
        (cards_dir / file_name).write_text(svg, encoding='utf-8')
    print(f'csv: {csv_path}')
    print(f'game_dir: {game_dir}')
    print(f'output_dir: {cards_dir}')
    print(f'generated: {len(rows)}')


if __name__ == '__main__':
    main()
