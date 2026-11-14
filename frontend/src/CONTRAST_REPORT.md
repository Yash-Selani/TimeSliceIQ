# TimeSliceIQ Design Tokens — WCAG 2.1 Contrast Report

> Generated via WCAG relative luminance formula.
> L = 0.2126·R + 0.7152·G + 0.0722·B (linearised sRGB).
> Contrast ratio = (L_lighter + 0.05) / (L_darker + 0.05).

## Results

| Foreground | Background | Ratio | Min Required | Result |
|---|---|---|---|---|
| --text (#F5F5F5) | --bg (#0D0D0D) | 17.83:1 | 4.5:1 (text) | PASS ✅ |
| --text-muted (#A3A3A3) | --bg (#0D0D0D) | 7.70:1 | 4.5:1 (text) | PASS ✅ |
| --accent (#FF6A00) | --bg (#0D0D0D) | 6.77:1 | 3:1 (UI) | PASS ✅ |
| --accent-ink (#0D0D0D) | --accent (#FF6A00) | 6.77:1 | 4.5:1 (text) | PASS ✅ |
| --danger (#FF5C5C) | --bg (#0D0D0D) | 6.42:1 | 3:1 (UI) | PASS ✅ |
| --text (#F5F5F5) | --surface (#151515) | 16.75:1 | 4.5:1 (text) | PASS ✅ |
| --text (#F5F5F5) | --surface-2 (#1E1E1E) | 15.29:1 | 4.5:1 (text) | PASS ✅ |
| --text-muted (#A3A3A3) | --surface (#151515) | 7.24:1 | 4.5:1 (text) | PASS ✅ |
| --text-muted (#A3A3A3) | --surface-2 (#1E1E1E) | 6.61:1 | 4.5:1 (text) | PASS ✅ |
| --rule (#2B2B2B) | --bg (#0D0D0D) | 1.37:1 | decorative (N/A) | N/A (decorative) |

## Summary

- **All text pairs** (foreground text on backgrounds): **PASS** — every ratio ≥ 4.5:1 (WCAG AA normal text).
- **All UI component pairs** (accent/danger on bg): **PASS** — every ratio ≥ 3:1 (WCAG AA non-text).
- **--rule on --bg**: 1.37:1 — intentionally low; used for decorative hairlines/separators only, not informational content.

> [!NOTE]
> `--accent-ink` on `--accent` (6.77:1) exceeds the 4.5:1 threshold, ensuring text rendered inside accent-colored buttons is fully legible.
