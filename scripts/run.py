"""Punto de entrada CLI: detecta, sigue y cuenta personas en un video.

Ejemplo:
    python scripts/run.py --source videos/tienda.mp4 --show
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.annotate import annotate_frame  # noqa: E402
from src.counter import PeopleCounter  # noqa: E402
from src.detector import PersonDetector  # noqa: E402
from src.io_video import create_writer, open_video, output_stem  # noqa: E402


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Detector y contador de personas en video (YOLO).")
    p.add_argument("--source", required=True, help="Ruta de video, URL o índice de cámara")
    p.add_argument("--config", default=str(ROOT / "config.yaml"), help="Archivo de configuración")
    p.add_argument("--model", help="Pesos YOLO (ej. yolo26n.pt, yolo26s.pt)")
    p.add_argument("--conf", type=float, help="Confianza mínima")
    p.add_argument("--iou", type=float, help="Umbral IoU")
    p.add_argument("--imgsz", type=int, help="Tamaño de inferencia")
    p.add_argument("--tracker", help="bytetrack.yaml o botsort.yaml")
    p.add_argument("--vid-stride", type=int, help="Procesar 1 de cada N frames (máx. recomendado 2)")
    p.add_argument("--device", help="cpu, 0, 1, ...")
    p.add_argument("--min-track-frames", type=int, help="Frames mínimos para contar un ID como único")
    p.add_argument("--output-dir", help="Carpeta de salida")
    p.add_argument("--log-every", type=int, help="Imprimir progreso cada N frames")
    p.add_argument("--show", action="store_true", help="Mostrar ventana con el video anotado (q para salir)")
    return p.parse_args()


def merge_settings(args: argparse.Namespace) -> dict[str, Any]:
    """CLI tiene prioridad sobre config.yaml."""
    settings = load_config(Path(args.config))
    for key, value in vars(args).items():
        if value is not None:
            settings[key] = value
    settings.setdefault("model", "yolo26n.pt")
    settings.setdefault("conf", 0.35)
    settings.setdefault("iou", 0.5)
    settings.setdefault("imgsz", 640)
    settings.setdefault("tracker", "bytetrack.yaml")
    settings.setdefault("vid_stride", 1)
    settings.setdefault("device", None)
    settings.setdefault("min_track_frames", 3)
    settings.setdefault("output_dir", "outputs")
    settings.setdefault("log_every", 30)
    settings.setdefault("default_fps", 30.0)
    settings["vid_stride"] = max(int(settings["vid_stride"]), 1)
    return settings


def log_progress(frame_idx: int, total: int, start: float, counter: PeopleCounter) -> None:
    elapsed = max(time.perf_counter() - start, 1e-6)
    fps = frame_idx / elapsed
    progress = f"{frame_idx}/{total} ({100 * frame_idx / total:.1f}%)" if total else str(frame_idx)
    print(
        f"[frame {progress}] {fps:.1f} FPS | en pantalla: {counter.in_frame} | "
        f"únicos: {counter.unique_count}",
        flush=True,
    )


def run(settings: dict[str, Any]) -> None:
    source = str(settings["source"])
    cap, info = open_video(source, settings["default_fps"])
    stride = settings["vid_stride"]
    out_path = ROOT / settings["output_dir"] / f"{output_stem(source)}_anotado.mp4"
    writer = create_writer(out_path, info, fps=info.fps / stride)

    print(f"Fuente: {source} | {info.width}x{info.height} @ {info.fps:.1f} FPS | frames: {info.total_frames or '?'}")
    print(f"Modelo: {settings['model']} | conf={settings['conf']} imgsz={settings['imgsz']} tracker={settings['tracker']}")

    detector = PersonDetector(
        settings["model"], settings["conf"], settings["iou"],
        settings["imgsz"], settings["tracker"], settings["device"],
    )
    counter = PeopleCounter(settings["min_track_frames"])

    frame_idx = 0
    processed = 0
    start = time.perf_counter()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame_idx += 1
            if (frame_idx - 1) % stride:
                continue

            dets = detector.track(frame)
            counter.update(len(dets.boxes), dets.track_ids)
            annotated = annotate_frame(frame, dets, counter.in_frame, counter.unique_count)
            writer.write(annotated)
            processed += 1

            if processed % settings["log_every"] == 0:
                log_progress(frame_idx, info.total_frames, start, counter)
            if settings.get("show"):
                cv2.imshow("Detector de personas", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("Interrumpido por el usuario.")
                    break
    except KeyboardInterrupt:
        print("Interrumpido con Ctrl+C; guardando lo procesado.")
    finally:
        cap.release()
        writer.release()
        cv2.destroyAllWindows()

    elapsed = time.perf_counter() - start
    print("\n=== Resumen ===")
    print(f"Frames procesados: {processed} en {elapsed:.1f} s ({processed / max(elapsed, 1e-6):.1f} FPS)")
    print(f"Personas únicas: {counter.unique_count}")
    print(f"Máximo simultáneo: {counter.max_simultaneous}")
    print(f"Video anotado: {out_path}")


def main() -> None:
    settings = merge_settings(parse_args())
    try:
        run(settings)
    except RuntimeError as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
