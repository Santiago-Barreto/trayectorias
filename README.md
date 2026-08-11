# Trayectorias — MapBiomas Colombia

Detección y corrección de trayectorias LULC anómalas (bosque / plantaciones) sobre la serie anual MapBiomas Colombia (Earth Engine).

## Stack

- Python + Jupyter (`Trayectorias_sos.ipynb`)
- Google Earth Engine (`earthengine-api`, `geemap` / `leafmap`)
- `pandas`, `plotly`, `matplotlib`

## Layout

```
Trayectorias_sos.ipynb   # flujo principal
src/                     # análisis y estadísticas
data/                    # leyenda + regiones
tests/
outputs/                 # generado (gitignored)
requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
jupyter notebook Trayectorias_sos.ipynb
```

Autenticación GEE local (`ee.Initialize`). Proyecto por defecto: `mapbiomas-colombia`.

## Config rápida

| Parámetro | Valores |
|-----------|---------|
| `REGION_ID` | `None` (nacional) o ID (ej. `30450`) |
| `VERSION_INPUT` | `1` / `>1` / `None` (auto) |
| `MODO_CORRECCION` | `bosque` \| `todas` |
| `MAPA_ANOMALIAS` | `bosque` \| `bosque_plantacion` \| `todas` |

Con `REGION_ID` definido: estadísticas de cobertura (ha) y mapa por año / ventanas 3–4–5. Sin él: mosaico nacional (sin mapa/stats pesados).

## Módulos

| Módulo | Rol |
|--------|-----|
| `src/paths.py` | Rutas `data/` / `outputs/` |
| `src/estadisticas_correccion.py` | Áreas original vs corregida |
| `src/analisis_nacional.py` | Figuras desde CSV de anomalías |
| `src/analisis_extremos.py` | Final de serie 2023–2025 |

## Tests

```bash
python tests/test_dual_map.py
python tests/test_estadisticas_correccion.py
```

## Nota

La documentación operativa detallada vive en `EXPLICACION.txt` (archivo local, no versionado).
