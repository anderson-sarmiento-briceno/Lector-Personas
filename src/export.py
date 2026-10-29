"""Exportación de resultados: CSV con conteos por segundo y JSON resumen."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

CSV_COLUMNS = ["segundo", "en_pantalla", "unicos_acumulados", "entradas_acum", "salidas_acum"]


@dataclass
class SecondRow:
    segundo: int
    en_pantalla: int        # máximo de personas visibles durante ese segundo
    unicos_acumulados: int
    entradas_acum: int
    salidas_acum: int


class PerSecondRecorder:
    """Agrega las métricas por frame en una fila por segundo de video."""

    def __init__(self, fps: float) -> None:
        self.fps = fps
        self.rows: dict[int, SecondRow] = {}

    def record(self, frame_idx: int, in_frame: int, unique: int, ins: int, outs: int) -> None:
        """`frame_idx` empieza en 1, igual que en run.py."""
        second = int((frame_idx - 1) / self.fps)
        row = self.rows.get(second)
        if row is None:
            self.rows[second] = SecondRow(second, in_frame, unique, ins, outs)
            return
        row.en_pantalla = max(row.en_pantalla, in_frame)
        row.unicos_acumulados, row.entradas_acum, row.salidas_acum = unique, ins, outs

    def to_dataframe(self) -> pd.DataFrame:
        data = [vars(r) for r in sorted(self.rows.values(), key=lambda r: r.segundo)]
        return pd.DataFrame(data, columns=CSV_COLUMNS)


TRACK_COLUMNS = ["frame", "track_id", "cx", "cy", "x1", "y1", "x2", "y2", "conf"]


class TrackRecorder:
    """Guarda cada detección con ID (en píxeles del video ORIGINAL) para re-contar sin el modelo."""

    def __init__(self, scale: float = 1.0) -> None:
        self.scale = scale
        self.rows: list[tuple[float, ...]] = []

    def record(self, frame_idx: int, track_ids: list[int | None], boxes: Any, confs: Any) -> None:
        k = 1.0 / self.scale
        for tid, (x1, y1, x2, y2), conf in zip(track_ids, boxes.tolist(), confs.tolist()):
            if tid is None:
                continue
            self.rows.append((frame_idx, tid, (x1 + x2) / 2 * k, (y1 + y2) / 2 * k,
                              x1 * k, y1 * k, x2 * k, y2 * k, round(conf, 3)))

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(self.rows, columns=TRACK_COLUMNS)
        df[["frame", "track_id"]] = df[["frame", "track_id"]].astype(int)
        df.round(1).to_csv(path, index=False)
        return path


def write_csv(recorder: PerSecondRecorder, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    recorder.to_dataframe().to_csv(path, index=False)
    return path


def write_json(summary: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
