# Trayectorias

Herramienta para detectar y corregir trayectorias temporales anómalas de **bosque** (clase 3) y **plantaciones** (9, 35, 74) en la colección MapBiomas Colombia.

## Contenido

- `Trayectorias_sos.ipynb` — flujo principal
- `analisis_nacional.py` — análisis nacional y regional
- `analisis_extremos.py` — análisis del final de la serie temporal
- `metodologia_correccion.txt` — descripción del método
- `regiones.xlsx` — regiones de clasificación
- `leyenda_coleccion3.json` — leyenda LULC
- `requirements.txt` — dependencias

## Uso

```bash
pip install -r requirements.txt
jupyter notebook Trayectorias_sos.ipynb
```

Parámetros principales en la celda de configuración:

| Parámetro | Valores |
|-----------|---------|
| `REGION_ID` | `None` (nacional) o ID de región |
| `MODO_CORRECCION` | `bosque` \| `todas` |
| `MAPA_ANOMALIAS` | `bosque` \| `bosque_plantacion` |

Ejecutar las celdas en orden.
