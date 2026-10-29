import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.export import CSV_COLUMNS, TRACK_COLUMNS, PerSecondRecorder, TrackRecorder, write_csv, write_json


def test_tracks_saved_in_original_pixels_and_skip_none(tmp_path: Path) -> None:
    rec = TrackRecorder(scale=0.5)
    boxes = np.array([[10, 20, 30, 60], [0, 0, 4, 4]], dtype=float)
    rec.record(7, [3, None], boxes, np.array([0.9, 0.4]))
    df = pd.read_csv(rec.write(tmp_path / "t.csv"))
    assert list(df.columns) == TRACK_COLUMNS
    assert df.to_dict("records") == [
        {"frame": 7, "track_id": 3, "cx": 40.0, "cy": 80.0,
         "x1": 20.0, "y1": 40.0, "x2": 60.0, "y2": 120.0, "conf": 0.9},
    ]


def test_rows_per_second_keep_max_and_last_cumulative() -> None:
    rec = PerSecondRecorder(fps=2)
    rec.record(1, in_frame=1, unique=1, ins=0, outs=0)
    rec.record(2, in_frame=3, unique=2, ins=1, outs=0)  # sigue en el segundo 0
    rec.record(3, in_frame=2, unique=3, ins=1, outs=1)  # segundo 1
    df = rec.to_dataframe()
    assert list(df.columns) == CSV_COLUMNS
    assert df.to_dict("records") == [
        {"segundo": 0, "en_pantalla": 3, "unicos_acumulados": 2, "entradas_acum": 1, "salidas_acum": 0},
        {"segundo": 1, "en_pantalla": 2, "unicos_acumulados": 3, "entradas_acum": 1, "salidas_acum": 1},
    ]


def test_write_files(tmp_path: Path) -> None:
    rec = PerSecondRecorder(fps=30)
    rec.record(1, 1, 1, 0, 0)
    csv_path = write_csv(rec, tmp_path / "a.csv")
    assert csv_path.read_text(encoding="utf-8").splitlines()[0] == ",".join(CSV_COLUMNS)
    json_path = write_json({"únicos": 1}, tmp_path / "a.json")
    assert json.loads(json_path.read_text(encoding="utf-8")) == {"únicos": 1}
