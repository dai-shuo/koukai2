# koukai2

Reverse engineering notes, tools, and extracted data for **大航海时代2 / Daikoukai Jidai II** on PC DOS.

This repository is intended to collect:

- code for save editing and binary analysis
- decoded tables and extracted data
- bitmap font research and character mappings
- documentation for reverse engineering findings

## Current Contents

### `hanzi/`

- `pat-map.csv`
  - merged mapping table for `1.PAT` and `2.PAT`
  - columns:
    - `pat`: source bitmap font file (`1.PAT` or `2.PAT`)
    - `index`: 1-based glyph index inside that PAT file
    - `unicode`: current Unicode code point
    - `char`: current character
    - `chs_unicode`: simplified-Chinese Unicode code point
    - `chs_char`: simplified-Chinese character

## Scope

This repo focuses on reverse engineering and tooling around:

- DOS executable internals
- save format research
- font / encoding mapping
- extracted game data

More tools, docs, and structured datasets can be added incrementally.
