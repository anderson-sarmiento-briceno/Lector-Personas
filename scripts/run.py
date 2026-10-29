"""Punto de entrada CLI: detecta, sigue y cuenta personas en un video.

Ejemplos:
    python scripts/run.py --source videos/tienda.mp4 --show
    python scripts/run.py --source videos/tienda.mp4 --line 120,400,1100,400
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.annotate import PanelValues, annotate_frame, centroids_of  # noqa: E402
from src.counter import LineCounter, PeopleCounter, Point, parse_line  # noqa: E402
from src.detector import PersonDetector  # noqa: E402
from src.export import PerSecondRecorder, TrackRecorder, write_csv, write_json  # noqa: E402
from src.io_video import VideoInfo, create_writer, open_video, output_stem, resize_scale, scaled_size  # noqa: E402

DEFAULTS: dict[str, Any] = {
    "model": "yolo26n.pt",
    "conf": 0.35,
    "iou": 0.5,
    "imgsz": 640,
    "tracker": "bytetrack.yaml",
    "vid_stride": 1,
    "device": None,
    "min_track_frames": 3,
    "line": None,
    "invert": False,
    "band": 0.0,
    "once_per_id": False,
    "max_width": None,
    "max_frames": None,
    "save_tracks": False,
    "output_dir": "outputs",
    "log_every": 30,
    "default_fps": 30.0,
    "show": False,
}
FLASH_SECONDS = 0.4  # cuánto tiempo se pinta de verde la línea tras un cruce


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
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
    p.add_argument("--min-track-frames", type=int, help="Frames mínimos de vida para contar un ID")
    p.add_argument("--line", help="Línea de conteo 'x1,y1,x2,y2' en píxeles del video ORIGINAL")
    p.add_argument("--invert", action="store_true", default=None, help="Invertir dirección ENTRADA/SALIDA")
    p.add_argument("--band", type=float, help="Zona muerta ±px (originales) alrededor de la línea; 0 = sin banda")
    p.add_argument("--once-per-id", action="store_true", default=None,
                   help="Cada ID cuenta una sola vez (primer cruce); evita rebotes en la puerta")
    p.add_argument("--max-width", type=int, help="Reducir frames más anchos que esto (ej. 1920 para 4K)")
    p.add_argument("--max-frames", type=int, help="Procesar solo los primeros N frames (pruebas)")
    p.add_argument("--save-tracks", action="store_true", default=None,
                   help="Guardar <video>_tracks.csv para re-contar con scripts/replay_line.py")
    p.add_argument("--output-dir", help="Carpeta de salida")
    p.add_argument("--log-every", type=int, help="Imprimir progreso cada N frames")
    p.add_argument("--show", action="store_true", default=None, help="Mostrar ventana (q para salir)")
    return p.parse_args(argv)


def merge_settings(args: argparse.Namespace) -> dict[str, Any]:
    """Prioridad: CLI > config.yaml > DEFAULTS."""
    settings = {**DEFAULTS, **load_config(Path(args.config))}
    for key, value in vars(args).items():
        if value is not None:
            settings[key] = value
    settings["vid_stride"] = max(int(settings["vid_stride"]), 1)
    return settings


def scale_line(line: tuple[Point, Point], scale: float) -> tuple[Point, Point]:
    (x1, y1), (x2, y2) = line
    return (x1 * scale, y1 * scale), (x2 * scale, y2 * scale)


def log_progress(frame_idx: int, total: int, start: float, people: PeopleCounter, line: LineCounter | None) -> None:
    elapsed = max(time.perf_counter() - start, 1e-6)
    progress = f"{frame_idx}/{total} ({100 * frame_idx / total:.1f}%)" if total else str(frame_idx)
    text = (
        f"[frame {progress}] {frame_idx / elapsed:.1f} FPS | en pantalla: {people.in_frame} | "
        f"únicos: {people.unique_count}"
    )
    if line is not None:
        text += f" | entradas: {line.in_count} | salidas: {line.out_count}"
    print(text, flush=True)


def build_summary(
    settings: dict[str, Any],
    info: VideoInfo,
    size: tuple[int, int],
    frames_read: int,
    processed: int,
    elapsed: float,
    people: PeopleCounter,
    line: LineCounter | None,
    outputs: dict[str, str],
) -> dict[str, Any]:
    """Resumen con todo lo necesario para respaldar los números (ver §9 de CLAUDE.md)."""
    import torch
    import ultralytics

    keys = ("model", "conf", "iou", "imgsz", "tracker", "vid_stride", "device",
            "min_track_frames", "line", "invert", "band", "once_per_id", "max_width")
    return {
        "fuente": str(settings["source"]),
        "fecha_proceso": datetime.now().isoformat(timespec="seconds"),
        "video": {
            "resolucion_original": [info.width, info.height],
            "resolucion_procesada": list(size),
            "fps": round(info.fps, 3),
            "frames_leidos": frames_read,
            "duracion_s": round(frames_read / info.fps, 2),
        },
        "resultados": {
            "unicos": people.unique_count,
            "max_simultaneo": people.max_simultaneous,
            "entradas": line.in_count if line else None,
            "salidas": line.out_count if line else None,
        },
        "eventos": [
            {"track_id": e.track_id, "direccion": e.direction, "frame": e.frame_idx,
             "segundo": round((e.frame_idx - 1) / info.fps, 2)}
            for e in (line.events if line else [])
        ],
        "parametros": {k: settings[k] for k in keys},
        "entorno": {
            "ultralytics": ultralytics.__version__,
            "torch": torch.__version__,
            "cuda": torch.cuda.is_available(),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "rendimiento": {
            "frames_procesados": processed,
            "segundos": round(elapsed, 2),
            "fps_procesamiento": round(processed / max(elapsed, 1e-6), 2),
        },
        "salidas": outputs,
    }


def run(settings: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta el pipeline completo y devuelve el resumen."""
    source = str(settings["source"])
    cap, info = open_video(source, settings["default_fps"])
    stride = settings["vid_stride"]
    scale = resize_scale(info.width, settings["max_width"])
    size = scaled_size(info, scale)

    out_dir = ROOT / settings["output_dir"]
    stem = output_stem(source)
    video_path = out_dir / f"{stem}_anotado.mp4"
    writer = create_writer(video_path, size, fps=info.fps / stride)

    line_pts = scale_line(parse_line(settings["line"]), scale) if settings["line"] else None
    band = float(settings["band"] or 0) * scale
    line_counter = (
        LineCounter(*line_pts, min_track_frames=settings["min_track_frames"],
                    invert=settings["invert"], band=band, once_per_id=settings["once_per_id"])
        if line_pts else None
    )
    people = PeopleCounter(settings["min_track_frames"])
    recorder = PerSecondRecorder(info.fps)
    tracks = TrackRecorder(scale) if settings["save_tracks"] else None

    print(f"Fuente: {source} | {info.width}x{info.height} @ {info.fps:.1f} FPS | frames: {info.total_frames or '?'}")
    if scale < 1:
        print(f"Procesando a {size[0]}x{size[1]} (escala {scale:.2f})")
    print(f"Modelo: {settings['model']} | conf={settings['conf']} imgsz={settings['imgsz']} tracker={settings['tracker']}")
    if line_pts:
        extras = f" | banda ±{settings['band']} px" if band else ""
        extras += " | invertida" if settings["invert"] else ""
        extras += " | 1 conteo por ID" if settings["once_per_id"] else ""
        print(f"Línea de conteo: {settings['line']} (original){extras}")

    detector = PersonDetector(
        settings["model"], settings["conf"], settings["iou"],
        settings["imgsz"], settings["tracker"], settings["device"],
    )

    frame_idx = processed = 0
    flash_until = 0
    start = time.perf_counter()
    try:
        while settings["max_frames"] is None or frame_idx < settings["max_frames"]:
            ok, frame = cap.read()
            if not ok:
                break
            frame_idx += 1
            if (frame_idx - 1) % stride:
                continue
            if scale < 1:
                frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)

            dets = detector.track(frame)
            people.update(len(dets.boxes), dets.track_ids)
            if tracks is not None:
                tracks.record(frame_idx, dets.track_ids, dets.boxes, dets.confidences)
            if line_counter is not None:
                for event in line_counter.update(dets.track_ids, centroids_of(dets.boxes), frame_idx):
                    verb = "ENTRA" if event.direction == "IN" else "SALE"
                    print(f"  -> ID {event.track_id} {verb} (t={(frame_idx - 1) / info.fps:.1f}s)", flush=True)
                    flash_until = frame_idx + int(FLASH_SECONDS * info.fps)

            ins = line_counter.in_count if line_counter else 0
            outs = line_counter.out_count if line_counter else 0
            recorder.record(frame_idx, people.in_frame, people.unique_count, ins, outs)

            values = PanelValues(
                people.in_frame, people.unique_count,
                ins if line_counter else None, outs if line_counter else None,
            )
            annotated = annotate_frame(frame, dets, values, line_pts, band=band, flash=frame_idx < flash_until)
            writer.write(annotated)
            processed += 1

            if processed % settings["log_every"] == 0:
                log_progress(frame_idx, info.total_frames, start, people, line_counter)
            if settings["show"]:
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
    csv_path = write_csv(recorder, out_dir / f"{stem}_conteo.csv")
    json_path = out_dir / f"{stem}_resumen.json"
    outputs = {"video": str(video_path), "csv": str(csv_path), "json": str(json_path)}
    if tracks is not None:
        outputs["tracks"] = str(tracks.write(out_dir / f"{stem}_tracks.csv"))
    summary = build_summary(settings, info, size, frame_idx, processed, elapsed, people, line_counter, outputs)
    write_json(summary, json_path)
    print_summary(summary)
    return summary


def print_summary(summary: dict[str, Any]) -> None:
    res, perf = summary["resultados"], summary["rendimiento"]
    print("\n=== Resumen ===")
    print(f"Frames procesados: {perf['frames_procesados']} en {perf['segundos']} s ({perf['fps_procesamiento']} FPS)")
    print(f"Personas únicas: {res['unicos']}")
    print(f"Máximo simultáneo: {res['max_simultaneo']}")
    if res["entradas"] is not None:
        print(f"Entradas: {res['entradas']} | Salidas: {res['salidas']}")
    for kind, path in summary["salidas"].items():
        print(f"{kind.upper()}: {path}")


def main() -> None:
    settings = merge_settings(parse_args())
    try:
        run(settings)
    except (RuntimeError, ValueError) as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
