"""Re-cuenta entradas/salidas a partir de <video>_tracks.csv, sin volver a correr el modelo.

Sirve para ajustar la posición de la línea y la banda en segundos.

Ejemplos:
    python scripts/run.py --source videos/v.mp4 --save-tracks          # una vez (lento)
    python scripts/replay_line.py --tracks outputs/v_tracks.csv --line 1600,800,1600,2160 --band 0 60 120
    python scripts/replay_line.py --tracks outputs/v_tracks.csv --line ... --expected-in 3 --expected-out 6
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.counter import LineCounter, parse_line  # noqa: E402


def replay(
    df: pd.DataFrame, line: str, band: float, min_track_frames: int, invert: bool, once_per_id: bool
) -> LineCounter:
    counter = LineCounter(*parse_line(line), min_track_frames=min_track_frames, invert=invert,
                          band=band, once_per_id=once_per_id)
    for frame_idx, group in df.groupby("frame", sort=True):
        counter.update(group["track_id"].tolist(), list(zip(group["cx"], group["cy"])), int(frame_idx))
    return counter


def error_pct(got: int, expected: int | None) -> str:
    if expected is None:
        return "-"
    if expected == 0:
        return "0%" if got == 0 else "inf"
    return f"{100 * abs(got - expected) / expected:.0f}%"


def main() -> None:
    p = argparse.ArgumentParser(description="Re-contar cruces de línea desde un CSV de tracks.")
    p.add_argument("--tracks", required=True, help="CSV generado con run.py --save-tracks")
    p.add_argument("--line", required=True, action="append", help="'x1,y1,x2,y2' (se puede repetir)")
    p.add_argument("--band", type=float, nargs="+", default=[0.0], help="Uno o varios valores de banda (px)")
    p.add_argument("--min-track-frames", type=int, default=3)
    p.add_argument("--invert", action="store_true")
    p.add_argument("--once-per-id", action="store_true", help="Cada ID cuenta una sola vez")
    p.add_argument("--fps", type=float, default=30.0, help="FPS del video, para mostrar segundos")
    p.add_argument("--expected-in", type=int, help="Entradas contadas a mano")
    p.add_argument("--expected-out", type=int, help="Salidas contadas a mano")
    p.add_argument("--events", action="store_true", help="Listar cada cruce")
    args = p.parse_args()

    df = pd.read_csv(args.tracks)
    print(f"{'línea':<24} {'banda':>6} {'IN':>4} {'OUT':>4} {'err IN':>7} {'err OUT':>8}")
    for line in args.line:
        for band in args.band:
            c = replay(df, line, band, args.min_track_frames, args.invert, args.once_per_id)
            print(f"{line:<24} {band:>6.0f} {c.in_count:>4} {c.out_count:>4} "
                  f"{error_pct(c.in_count, args.expected_in):>7} {error_pct(c.out_count, args.expected_out):>8}")
            if args.events:
                for e in c.events:
                    print(f"    ID {e.track_id:<5} {e.direction:<3} t={(e.frame_idx - 1) / args.fps:.1f}s")


if __name__ == "__main__":
    main()
