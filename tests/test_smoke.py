"""Prueba de humo: corre el pipeline completo sobre los primeros frames de un video real.

Se omite si no está el video de prueba o falta ultralytics.
"""
import json
from pathlib import Path

import pytest

pytest.importorskip("ultralytics")

from scripts.run import merge_settings, parse_args, run  # noqa: E402

VIDEO = Path(__file__).resolve().parents[1] / "videos" / "hombre_entrando_tienda.mp4"


@pytest.mark.skipif(not VIDEO.exists(), reason="falta videos/hombre_entrando_tienda.mp4")
def test_pipeline_produces_outputs(tmp_path: Path) -> None:
    args = parse_args([
        "--source", str(VIDEO), "--max-frames", "45", "--max-width", "960",
        "--line", "1600,0,1600,2160", "--output-dir", str(tmp_path), "--log-every", "1000",
    ])
    summary = run(merge_settings(args))

    for key in ("video", "csv", "json"):
        assert Path(summary["salidas"][key]).stat().st_size > 0
    assert summary["video"]["resolucion_procesada"] == [960, 540]
    assert summary["rendimiento"]["frames_procesados"] == 45
    assert summary["resultados"]["max_simultaneo"] >= 1
    assert summary["resultados"]["entradas"] is not None
    saved = json.loads(Path(summary["salidas"]["json"]).read_text(encoding="utf-8"))
    assert saved["resultados"] == summary["resultados"]
