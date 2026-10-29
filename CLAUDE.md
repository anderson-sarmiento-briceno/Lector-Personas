# CLAUDE.md — Detector y Contador de Personas en Video (YOLO)

> Este archivo es el contexto que Claude Code lee al trabajar en este repositorio.
> Explica **qué** construimos, **por qué**, **cómo** está organizado y **qué reglas** seguir.
> Idioma del proyecto: **español** (código y nombres de variables en inglés; comentarios, docs y mensajes al usuario en español).

---

## 1. Objetivo del proyecto

Construir una herramienta en Python que:

1. Reciba un **video** (archivo `.mp4`, `.avi`, `.mov`, o una URL/stream).
2. **Detecte personas** en cada fotograma con un modelo YOLO.
3. **Siga (tracking)** a cada persona entre fotogramas asignándole un **ID único**.
4. **Marque** a cada persona en el video (caja + ID) y muestre un **contador en pantalla**.
5. **Cuente** personas de tres formas (ver sección 4):
   - Personas visibles **en este momento** (por fotograma).
   - Personas **únicas** que aparecieron en todo el video.
   - Personas que **cruzan una línea** o zona, separando **ENTRADAS / SALIDAS** (caso negocio).
6. Exporte:
   - Un **video anotado** (`outputs/<nombre>_anotado.mp4`).
   - Un **CSV** con conteos por segundo y un **JSON** con el resumen.

**Meta final (fase posterior):** usar las salidas reales del modelo para producir un **video publicitario**.
Por eso todo lo que se muestre en el anuncio debe salir del modelo real (nada de cajas dibujadas a mano ni números inventados) y los videos de origen deben tener **licencia que permita uso comercial** (ver sección 9).

---

## 2. Stack tecnológico

| Componente | Elección | Por qué |
|---|---|---|
| Lenguaje | Python 3.10 – 3.12 | Compatible con Ultralytics y OpenCV |
| Detección | **Ultralytics YOLO26** (`yolo26n.pt` por defecto) | Último modelo de Ultralytics, rápido, sin NMS, corre bien en CPU |
| Respaldo | `yolo11n.pt` | Si YOLO26 da problemas con la versión instalada |
| Tracking | **ByteTrack** (`bytetrack.yaml`) o BoT-SORT (`botsort.yaml`), integrados en Ultralytics | Asigna IDs persistentes → permite contar personas únicas |
| Conteo por línea/zona | `ultralytics.solutions.ObjectCounter` y `RegionCounter` | Conteo IN/OUT listo para usar |
| Video | OpenCV (`opencv-python`) | Lectura/escritura de frames |
| Datos | `pandas` | CSV de resultados |
| Opcional | `supervision` (Roboflow) | Anotaciones más bonitas para el video publicitario |
| Opcional | `yt-dlp` | Descargar videos **solo para pruebas** (ver sección 9) |

En el dataset COCO, con el que vienen entrenados los modelos YOLO, la clase **`0` = `person`**. Siempre filtramos con `classes=[0]`.

---

## 3. Estructura del repositorio

```
detector-personas/
├── CLAUDE.md                # este archivo
├── README.md                # guía corta para humanos
├── requirements.txt
├── config.yaml              # parámetros por defecto (modelo, conf, línea, etc.)
├── videos/                  # videos de entrada (NO se suben a git)
│   └── .gitkeep
├── outputs/                 # videos anotados, CSV, JSON (NO se suben a git)
│   └── .gitkeep
├── models/                  # pesos .pt descargados (NO se suben a git)
├── src/
│   ├── __init__.py
│   ├── detector.py          # carga del modelo + detección/tracking por frame
│   ├── counter.py           # lógica de conteo (frame, únicos, línea IN/OUT)
│   ├── annotate.py          # dibujo de cajas, IDs, línea y panel de conteo
│   ├── io_video.py          # abrir video/URL, escribir video de salida
│   ├── export.py            # CSV por segundo + JSON resumen
│   └── pick_line.py         # herramienta: clic en el 1er frame para definir la línea
├── scripts/
│   ├── run.py               # punto de entrada CLI
│   └── download_test_videos.md  # lista de videos de prueba y cómo obtenerlos
└── tests/
    ├── test_counter.py      # pruebas unitarias de la lógica de cruce de línea
    └── test_smoke.py        # corre el pipeline sobre un clip corto
```

`.gitignore` debe incluir: `videos/*`, `outputs/*`, `models/*`, `*.pt`, `.venv/`, `__pycache__/`.

---

## 4. Conceptos clave (léelos antes de tocar el código)

### 4.1 Detección vs. tracking vs. conteo
- **Detección:** en cada frame, YOLO devuelve cajas `[x1, y1, x2, y2]`, confianza y clase. No sabe si la persona del frame 10 es la misma del frame 11.
- **Tracking:** el tracker (ByteTrack/BoT-SORT) asocia detecciones entre frames y asigna un **`track_id`**. Así sabemos que es la misma persona.
- **Conteo:** se construye **sobre** el tracking. Sin IDs no se puede contar personas únicas ni entradas/salidas sin contar doble.

### 4.2 Los tres tipos de conteo
| Tipo | Qué responde | Cómo se calcula |
|---|---|---|
| **Por frame** | "¿Cuántas personas hay ahora mismo en cámara?" (aforo) | `len(boxes)` del frame actual |
| **Únicos** | "¿Cuántas personas distintas pasaron por el video?" | `len(set(track_ids_vistos))` |
| **Cruce de línea** | "¿Cuántas personas **entraron** y cuántas **salieron** del negocio?" | Se toma el **centroide** de cada `track_id`; cuando pasa de un lado de la línea al otro se suma IN u OUT según la dirección. Cada ID cuenta **una sola vez por dirección**. |

> ⚠️ El conteo de "únicos" **sobreestima** cuando hay oclusiones: si una persona desaparece detrás de otra y reaparece, el tracker puede darle un ID nuevo. Para negocios, el conteo **por cruce de línea** es el más confiable y el que tiene sentido de negocio.

### 4.3 Dónde poner la línea de conteo
- Perpendicular a la dirección del flujo, justo en la **puerta/umbral**.
- En una zona donde las personas se vean **completas** y **separadas** (no donde se amontonan).
- Ni muy al borde del frame (el tracker aún no estabiliza el ID) ni detrás de obstáculos.
- Se define en **píxeles** del video original. Usar `src/pick_line.py` para elegirla con clics.

### 4.4 Parámetros que más afectan el resultado
| Parámetro | Valor inicial | Efecto |
|---|---|---|
| `conf` | `0.35` | Más alto = menos falsos positivos pero se pierden personas lejanas |
| `iou` | `0.5` | Solapamiento para unir cajas |
| `imgsz` | `640` (`960`–`1280` si las personas son pequeñas) | Más grande = mejor en multitudes, más lento |
| `tracker` | `bytetrack.yaml` | `botsort.yaml` recupera mejor IDs tras oclusiones, algo más lento |
| `vid_stride` | `1` | Saltar frames acelera pero empeora el tracking; no subir de 2 |
| modelo | `yolo26n` → `yolo26s` → `yolo26m` | Más grande = más preciso y más lento |

---

## 5. Instalación

### Windows (PowerShell, VS Code)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### `requirements.txt`
```
ultralytics>=8.3
opencv-python
pandas
pyyaml
lapx            # requerido por los trackers de Ultralytics
supervision     # opcional, para anotaciones del video publicitario
yt-dlp          # opcional, solo pruebas
pytest
```

GPU (opcional): instalar PyTorch con CUDA desde pytorch.org **antes** de `ultralytics`. Verificar con:
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

Los pesos (`yolo26n.pt`) se descargan solos la primera vez que se cargan.

---

## 6. Cómo se usa (CLI objetivo)

```bash
# 1) Solo detectar y contar personas visibles + únicas
python scripts/run.py --source videos/tienda.mp4

# 2) Elegir la línea de conteo con clics sobre el primer frame
python src/pick_line.py --source videos/tienda.mp4
#    -> imprime algo como:  --line 120,400,1100,400

# 3) Contar entradas/salidas cruzando la línea
python scripts/run.py --source videos/tienda.mp4 --line 120,400,1100,400 --show

# 4) Ajustes
python scripts/run.py --source videos/calle.mp4 --model yolo26s.pt --imgsz 960 --conf 0.3 --tracker botsort.yaml
```

Atajo usando solo Ultralytics (útil para una prueba rápida, sin nuestro código):
```bash
yolo solutions count source="videos/tienda.mp4" region="[(20, 400), (1080, 400)]" show=True
```

Salidas esperadas en `outputs/`:
- `tienda_anotado.mp4` — video con cajas, IDs, línea y panel "EN PANTALLA / ÚNICOS / ENTRADAS / SALIDAS".
- `tienda_conteo.csv` — columnas: `segundo, en_pantalla, unicos_acumulados, entradas_acum, salidas_acum`.
- `tienda_resumen.json` — totales, máximo de personas simultáneas, duración, modelo y parámetros usados, FPS de procesamiento.

---

## 7. Código de referencia

### 7.1 Versión rápida con `ObjectCounter` (Ultralytics Solutions)
```python
import cv2
from ultralytics import solutions

def count_people_line(src: str, dst: str, line: list[tuple[int, int]], model: str = "yolo26n.pt"):
    cap = cv2.VideoCapture(src)
    assert cap.isOpened(), f"No se pudo abrir {src}"
    w, h, fps = (int(cap.get(p)) for p in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))
    out = cv2.VideoWriter(dst, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    counter = solutions.ObjectCounter(
        model=model,
        region=line,          # 2 puntos = línea; 3+ puntos = polígono
        classes=[0],          # solo personas
        show=False,
    )
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        res = counter(frame)
        out.write(res.plot_im)

    cap.release(); out.release()
    print("Entradas:", res.in_count, "Salidas:", res.out_count)
```

### 7.2 Versión propia (control total: únicos, por frame, CSV)
```python
import cv2
from ultralytics import YOLO

model = YOLO("yolo26n.pt")
seen_ids: set[int] = set()

for r in model.track(source="videos/tienda.mp4", classes=[0], conf=0.35,
                     tracker="bytetrack.yaml", persist=True, stream=True):
    boxes = r.boxes
    in_frame = len(boxes)
    if boxes.id is not None:                 # puede ser None si no hay tracks aún
        ids = boxes.id.int().tolist()
        seen_ids.update(ids)
        centroids = ((boxes.xyxy[:, :2] + boxes.xyxy[:, 2:]) / 2).tolist()
        # -> pasar (ids, centroids) a counter.LineCounter.update(...)
    frame = r.plot()                          # o annotate.draw(...) propio
```

### 7.3 Lógica de cruce de línea (`src/counter.py`)
- Guardar el **último lado** de la línea para cada `track_id` usando el signo del producto cruz:
  `side = sign((x2-x1)*(cy-y1) - (y2-y1)*(cx-x1))`.
- Si el signo cambia de `-` a `+` → `IN`; de `+` a `-` → `OUT` (la dirección se puede invertir con `--invert`).
- Además verificar que el centroide esté **dentro del segmento** (no en la prolongación de la línea).
- Un ID se cuenta **una vez por dirección** (`counted_in`, `counted_out` como sets).
- Ignorar tracks con menos de N frames de vida (`min_track_frames=3`) para evitar ruido.
- **Esta lógica debe tener pruebas unitarias** con trayectorias sintéticas (sin video).

---

## 8. Videos de prueba (con contexto de negocio)

Guardar los videos descargados en `videos/` con nombres descriptivos. Para cada uno, anotar en `scripts/download_test_videos.md`: fuente, licencia, resolución, dónde va la línea y el conteo esperado (contado a mano) para medir el error.

### Caso A — Conteo de clientes que entran a un negocio (caso principal)
| Video | Fuente / licencia | Por qué sirve |
|---|---|---|
| Personas entrando a un supermercado con puertas automáticas — https://www.pexels.com/video/people-going-inside-a-store-with-automatic-sliding-doors-6641527/ | Pexels (uso comercial libre) | Puerta clara para poner la línea de entrada |
| Clientes entrando y saliendo de un restaurante — https://www.pexels.com/video/customers-going-in-and-out-of-restaurant-6589392/ | Pexels, 4K, 57 s, cámara fija | **Ideal**: entradas y salidas → probar IN/OUT |
| Hombre entrando a una tienda — https://www.pexels.com/video/man-walking-into-a-store-6685167/ | Pexels, 4K, 16 s | Caso simple, una persona: prueba de humo |
| CAVIAR – pasillo de centro comercial en Lisboa (clientes entran/salen de tiendas) — https://homepages.inf.ed.ac.uk/rbf/CAVIARDATA1/ | Investigación, CC BY-SA, **trae ground truth** | Permite **medir precisión** contra conteos reales; vista de cámara de seguridad |

### Caso B — Flujo peatonal frente a un local (¿vale la pena esa ubicación / vitrina?)
| Video | Fuente | Por qué sirve |
|---|---|---|
| Intersección con tiendas, cámara fija — https://www.pexels.com/video/people-crossing-the-street-5631418/ | Pexels | Contar peatones que pasan frente a locales |
| Calle de París en ángulo alto, 48 s — https://www.pexels.com/video/moving-cars-and-people-crossing-the-street-4979728/ | Pexels | Personas + autos: verificar que solo cuente personas |
| Andén con peatones, 16 s — https://www.pexels.com/video/people-walking-by-on-a-sidewalk-854100/ | Pexels | Línea a lo largo de la acera |

### Caso C — Aforo / multitudes (eventos, estaciones, plazas)
| Video | Fuente | Por qué sirve |
|---|---|---|
| Cruce de Shibuya, vista alta — https://www.pexels.com/video/a-large-crowd-of-people-are-standing-in-the-middle-of-a-street-19743475/ | Pexels | Prueba de estrés: cientos de personas, usar `imgsz 1280` |
| Multitud urbana vista desde arriba (vertical 9:16) — https://www.pexels.com/video/aerial-view-of-busy-urban-crowd-movement-37307217/ | Pexels | Formato vertical, útil para reels publicitarios |
| MOT20 (estación de tren, salida de estadio, plaza nocturna) — https://motchallenge.net/data/MOT20 | Benchmark académico, **ground truth**, uso de investigación | Medir el modelo en multitudes muy densas |
| MOT17 — https://motchallenge.net/ | Benchmark académico | Peatones con cámara en movimiento |

### Caso D — Centro comercial / pasillos (zonas calientes)
- Mixkit, categoría *mall*: https://mixkit.co/free-stock-video/mall/ (revisar licencia por clip).
- Usar `RegionCounter` con varias zonas (pasillo, vitrina, caja) para ver dónde se concentra la gente.

### YouTube y otras plataformas
- Términos útiles: `store entrance cctv footage`, `people counting test video`, `shop door camera customers`, `cámara de seguridad entrada tienda`, `mall cctv crowd`.
- **Solo para pruebas internas.** Descargar videos de YouTube puede violar sus Términos de Servicio y el contenido tiene derechos de autor: **nunca** usarlos en el video publicitario.
- Evitar datasets con problemas de consentimiento para material público (ej. *Oxford Town Centre*: grabado de una cámara de vigilancia pública sin consentimiento de los peatones).

---

## 9. Licencias, ética y privacidad (importante para la fase publicitaria)

1. **Ultralytics YOLO es AGPL-3.0.** Usarlo para pruebas, estudio o un proyecto open source está bien. Si el producto se **vende o se ofrece como servicio cerrado**, hay que publicar el código bajo AGPL o comprar la **licencia Enterprise** de Ultralytics. Tenerlo presente antes de comercializar.
2. **Videos para el anuncio:** usar solo fuentes con permiso comercial (Pexels; Pixabay; Mixkit revisando cada clip) **o grabaciones propias con autorización** del negocio y aviso visible de cámara. Guardar el enlace y la licencia de cada clip usado.
3. **No reconocimiento facial.** El sistema solo cuenta cajas con IDs temporales; no identifica a nadie. No agregar funciones de identificación.
4. **Opción `--blur-faces`** (fase 3): difuminar rostros/personas en el video de salida para material público.
5. **Honestidad en el anuncio:** los números mostrados deben ser los que realmente produjo el modelo. Incluir en el JSON el modelo, versión y parámetros usados para poder respaldarlo.

---

## 10. Hoja de ruta

- **Fase 1 — MVP**: `run.py` con detección + tracking + conteo por frame y únicos + video anotado. Probar con los videos del Caso A.
- **Fase 2 — Negocio**: línea IN/OUT, `pick_line.py`, CSV/JSON, pruebas unitarias de `counter.py`, medir error vs. conteo manual (meta: error < 10 % en el Caso A).
- **Fase 3 — Robustez**: zonas múltiples (`RegionCounter`), `--blur-faces`, comparación ByteTrack vs BoT-SORT, YOLO26n vs YOLO26s, informe de FPS en CPU/GPU.
- **Fase 4 — Video publicitario**: anotaciones con estilo de marca (supervision), panel de conteo animado, gráfica de entradas por minuto a partir del CSV, versión vertical 9:16 para redes sociales.

---

## 11. Reglas para Claude Code en este repo

- Responder y comentar en **español**; nombres de funciones/variables en **inglés** y `snake_case`.
- Python con **type hints**, funciones pequeñas, sin variables globales (salvo constantes).
- Todos los parámetros configurables por **CLI (`argparse`) y/o `config.yaml`**; nada de rutas fijas en el código.
- Antes de cambiar `counter.py`, **correr `pytest`**; toda lógica nueva de conteo debe venir con prueba.
- No subir videos, pesos `.pt` ni salidas a git.
- Manejar con cuidado: `boxes.id` puede ser `None`; videos con FPS = 0 (usar 30 por defecto); URLs que no abren.
- Mostrar barra de progreso o log cada N frames con FPS de procesamiento.
- Si un cambio afecta la precisión del conteo, reportar el conteo antes/después sobre el mismo video.
- No implementar reconocimiento facial ni identificación de personas.

### Comandos frecuentes
```bash
pytest -q                                            # pruebas
python scripts/run.py --source videos/<v>.mp4 --show # corrida con ventana
python src/pick_line.py --source videos/<v>.mp4      # elegir línea
```

---

## 12. Problemas conocidos y soluciones

| Síntoma | Causa probable | Solución |
|---|---|---|
| Cuenta de más en "únicos" | IDs que cambian por oclusión | Usar `botsort.yaml`, subir `imgsz`, confiar en el conteo por línea |
| No detecta gente lejana | Personas muy pequeñas | `imgsz 960/1280`, modelo `s` o `m`, bajar `conf` a 0.25 |
| Cuenta maniquíes, carteles o reflejos | Falsos positivos | Subir `conf`, definir zona (polígono) que excluya la vitrina |
| Cuenta doble en la puerta | Gente que se queda parada sobre la línea | Usar zona (banda de 2 líneas) o `min_track_frames` más alto |
| Video de salida no abre | Códec | Probar `avc1` o reconvertir con `ffmpeg -i in.mp4 -vcodec libx264 out.mp4` |
| Muy lento en CPU | Modelo grande / 4K | `yolo26n`, `imgsz 640`, redimensionar el video a 1080p o 720p |
