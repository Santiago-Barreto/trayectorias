# Trayectorias — MapBiomas Colombia

Detección y corrección de trayectorias anómalas en la serie anual de coberturas MapBiomas Colombia (Google Earth Engine).

## Requisitos

```bash
pip install -r requirements.txt
```

Autenticación GEE local (`ee.Initialize`). Proyecto por defecto: `mapbiomas-colombia`.

## Uso

Abrir `Trayectorias_sos.ipynb` y ejecutar las celdas en orden.

En **Configuración**, parámetros editables:

| Parámetro | Opciones |
|-----------|----------|
| `FOLDER` | `FOLDER_FT` \| `FOLDER_CLASS` |
| `REGION_ID` | `None` (nacional) \| id (ej. `30450`) |
| `VERSION_INPUT` | `1` \| `>1` \| `None` |
| `REEXPORTAR` | `False` \| `True` (CSV de anomalías) |
| `REEXPORTAR_STATS` | `False` \| `True` (recalcula ha en GEE) |
| `MAPA_ANOMALIAS` | `bosque` \| `bosque_plantacion` \| `todas` |
| `CORREGIR_BORDES` | `False` \| `True` |
| `VENTANAS_HUECOS` | `(3,)` \| `(3, 4)` |

## Método

1. Huecos de 1–2 años en bosque (clase 3) y plantaciones (9, 35, 74) se rellenan.
2. Islas cortas (1–2 años) de bosque o plantación se sustituyen por el contexto.

Patrones de ≥3 años se conservan. El notebook muestra mapa de anomalías, tablas de patrones y estadísticas de área (ha) original vs corregida.

Con `REGION_ID` definido: mapa y estadísticas regionales. Con `None`: mosaico nacional (sin mapa interactivo ni stats de cobertura).

Salidas en `outputs/` (CSV de anomalías y coberturas por región).

## Estructura

```
Trayectorias_sos.ipynb
src/           # rutas, análisis, estadísticas
data/          # leyenda y regiones
tests/
outputs/       # generado (gitignored)
requirements.txt
```

| Módulo | Rol |
|--------|-----|
| `src/paths.py` | Rutas `data/` / `outputs/` |
| `src/estadisticas_correccion.py` | Áreas original vs corregida |
| `src/analisis_nacional.py` | Figuras desde CSV de anomalías |
| `src/analisis_extremos.py` | Final de serie 2023–2025 |

## Tests

```bash
python tests/test_dual_map.py
python tests/test_reglas_correccion.py
python tests/test_estadisticas_correccion.py
```
