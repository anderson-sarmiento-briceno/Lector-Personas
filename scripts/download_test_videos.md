# 🎞️ Videos de prueba

Registro de cada video usado: fuente, licencia, dónde va la línea y el conteo esperado (contado a mano) para medir el error.
Los videos se guardan en `videos/` (fuera de git).

## Cómo descargar (Pexels)

```powershell
curl.exe -L -A "Mozilla/5.0" -o videos/<nombre>.mp4 "https://www.pexels.com/download/video/<ID>/"
```

---

## ✅ `hombre_entrando_tienda.mp4`

| Campo | Valor |
|:--|:--|
| Fuente | https://www.pexels.com/video/man-walking-into-a-store-6685167/ |
| Licencia | Pexels (uso comercial libre, sin atribución obligatoria) |
| Resolución | 3840×2160 · 29.97 FPS · 478 frames (16 s) |
| Escena | Floristería por dentro: un cliente entra y habla con la vendedora |
| Línea | No aplica (no hay un umbral claro; se usa para únicos/por frame) |
| **Esperado (manual)** | **2 personas únicas**, máximo 2 simultáneas |
| Uso | Prueba de humo (`tests/test_smoke.py`) |

## ✅ `restaurante_entradas_salidas.mp4`

| Campo | Valor |
|:--|:--|
| Fuente | https://www.pexels.com/video/customers-going-in-and-out-of-restaurant-6589392/ |
| Licencia | Pexels (uso comercial libre) |
| Resolución | 3840×2160 · 29.97 FPS · 1694 frames (56.5 s) |
| Escena | Acera frente a la puerta de un restaurante; cámara fija; la puerta queda a la izquierda |
| Línea | `--line 1500,800,1500,2160` (vertical, junto al marco derecho de la puerta). Derecha → izquierda = ENTRA |
| **Esperado (manual)** | **3 entradas, 6 salidas** |

Conteo manual (revisado con hojas de contacto cada 0.5 s):

| t (s) | Evento | Persona |
|:--:|:--:|:--|
| ~17 | SALE | hombre chaqueta verde/azul |
| ~19 | SALE | mujer chaqueta rosada |
| ~22 | SALE | mujer abrigo verde oscuro, mochila |
| ~30 | SALE | mujer abrigo negro largo |
| ~32 | SALE | hombre camisa a cuadros (luego se queda sosteniendo la puerta sobre la línea) |
| ~37 | ENTRA | chica buzo negro, jeans rotos |
| ~38 | ENTRA | chica gorro blanco |
| ~45 | SALE | mujer chaleco rojo |
| ~45.5 | ENTRA | hombre gorro negro, buzo gris |

> ⚠️ Dificultades: la puerta de vidrio corta los tracks (reflejos/oclusión), gente muy cerca de la cámara y una persona parada sobre la línea varios segundos.

## ✅ `supermercado_puertas.mp4`

| Campo | Valor |
|:--|:--|
| Fuente | https://www.pexels.com/video/people-going-inside-a-store-with-automatic-sliding-doors-6641527/ |
| Licencia | Pexels (uso comercial libre) |
| Resolución | 2560×1440 · 29.97 FPS · 592 frames (19.8 s) |
| Escena | Entrada de supermercado con puertas corredizas automáticas; la gente llega por la acera desde la izquierda |
| Línea | `--line 750,400,750,1440 --invert` (vertical, borde izquierdo de la puerta). Izquierda → derecha = ENTRA |
| **Esperado (manual)** | **4 entradas, 1 salida** |

| t (s) | Evento | Persona |
|:--:|:--:|:--|
| ~2 | ENTRA | hombre camisa a cuadros roja, gorra morada |
| ~3 | ENTRA | hombre camisa a cuadros azul |
| ~12.5 | ENTRA | mujer chaqueta verde, botas |
| ~14 | ENTRA | hombre abrigo negro, gorra verde |
| ~18 | SALE | hombre chaleco verde, mangas amarillas |

> Al final (19–19.5 s) se ve a alguien dentro de la tienda que **no** llega a salir: no cuenta.

---

## 🔜 Pendientes (ver §8 de `CLAUDE.md`)

| Video | Caso | Para qué |
|:--|:--|:--|
| CAVIAR (Edimburgo) | A | Medir contra *ground truth* oficial |
| Intersección con tiendas (Pexels 5631418) | B | Flujo peatonal |
| Shibuya (Pexels 19743475) | C | Estrés con multitudes, `imgsz 1280` |
