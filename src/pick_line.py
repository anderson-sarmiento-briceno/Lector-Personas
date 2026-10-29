"""Herramienta: elegir la línea de conteo con dos clics sobre un frame del video.

Uso:
    python src/pick_line.py --source videos/tienda.mp4 [--frame 0]

Controles: clic izquierdo = punto, r = reiniciar, Enter/espacio = confirmar, q/Esc = salir.
Imprime la línea en píxeles del video ORIGINAL, lista para --line.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.io_video import open_video  # noqa: E402

WINDOW = "Elegir linea (clic x2, Enter confirma, r reinicia, q sale)"
MAX_DISPLAY = (1280, 720)
KEY_ENTER, KEY_SPACE, KEY_ESC = 13, 32, 27


def display_scale(width: int, height: int, max_size: tuple[int, int] = MAX_DISPLAY) -> float:
    """Factor para que el frame quepa en pantalla (nunca agranda)."""
    return min(max_size[0] / width, max_size[1] / height, 1.0)


def to_original(points: list[tuple[int, int]], scale: float) -> list[tuple[int, int]]:
    return [(round(x / scale), round(y / scale)) for x, y in points]


def format_line(points: list[tuple[int, int]]) -> str:
    (x1, y1), (x2, y2) = points
    return f"{x1},{y1},{x2},{y2}"


def read_frame(source: str, frame_number: int) -> np.ndarray:
    cap, _ = open_video(source)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"No se pudo leer el frame {frame_number} de {source}")
    return frame


def render(base: np.ndarray, points: list[tuple[int, int]]) -> np.ndarray:
    img = base.copy()
    for p in points:
        cv2.circle(img, p, 6, (255, 80, 255), -1)
    if len(points) == 2:
        cv2.line(img, points[0], points[1], (255, 80, 255), 2)
    return img


def pick(frame: np.ndarray) -> list[tuple[int, int]] | None:
    """Abre la ventana y devuelve los 2 puntos en coordenadas de pantalla (o None)."""
    scale = display_scale(frame.shape[1], frame.shape[0])
    base = cv2.resize(frame, None, fx=scale, fy=scale) if scale < 1 else frame
    points: list[tuple[int, int]] = []

    def on_mouse(event: int, x: int, y: int, *_: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 2:
            points.append((x, y))

    cv2.namedWindow(WINDOW)
    cv2.setMouseCallback(WINDOW, on_mouse)
    try:
        while True:
            cv2.imshow(WINDOW, render(base, points))
            key = cv2.waitKey(20) & 0xFF
            if key in (ord("q"), KEY_ESC):
                return None
            if key == ord("r"):
                points.clear()
            if key in (KEY_ENTER, KEY_SPACE) and len(points) == 2:
                return to_original(points, scale)
    finally:
        cv2.destroyAllWindows()


def main() -> None:
    p = argparse.ArgumentParser(description="Elegir la línea de conteo con clics.")
    p.add_argument("--source", required=True, help="Video o URL")
    p.add_argument("--frame", type=int, default=0, help="Número de frame a mostrar")
    args = p.parse_args()
    try:
        points = pick(read_frame(args.source, args.frame))
    except RuntimeError as e:
        sys.exit(f"Error: {e}")
    if points is None:
        print("Cancelado.")
        return
    print(f"--line {format_line(points)}")


if __name__ == "__main__":
    main()
