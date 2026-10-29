# Lector de Personas

Detecta, sigue y cuenta personas en video con Ultralytics YOLO + ByteTrack.

## Instalación (Windows)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uso
```bash
python scripts/run.py --source videos/tienda.mp4 --show
python scripts/run.py --source videos/calle.mp4 --model yolo26s.pt --imgsz 960 --conf 0.3
```
Salida: `outputs/<nombre>_anotado.mp4` con cajas, IDs y panel de conteo (en pantalla / únicos).

Los parámetros por defecto están en `config.yaml`; los argumentos de CLI tienen prioridad.

## Pruebas
```bash
pytest -q
```

## Licencia
Usa Ultralytics YOLO (AGPL-3.0). Ver sección 9 de `CLAUDE.md` antes de uso comercial.
