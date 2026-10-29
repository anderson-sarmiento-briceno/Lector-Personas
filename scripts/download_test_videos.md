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

---

## 🔜 Pendientes (ver §8 de `CLAUDE.md`)

| Video | Caso | Para qué |
|:--|:--|:--|
| Supermercado puertas automáticas (Pexels 6641527) | A | Segunda prueba de ENTRADAS |
| CAVIAR (Edimburgo) | A | Medir contra *ground truth* oficial |
| Intersección con tiendas (Pexels 5631418) | B | Flujo peatonal |
| Shibuya (Pexels 19743475) | C | Estrés con multitudes, `imgsz 1280` |
