# Trayectorias

Detección y corrección de **bosque aislado** (clase 3) y plantaciones cortas (9, 35, 74) en MapBiomas Colombia.

## Archivos

| Archivo | Uso |
|---------|-----|
| `Trayectorias_sos.ipynb` | Flujo principal (GEE, mapa, análisis) |
| `analisis_nacional.py` | Gráficos nacional / regional |
| `analisis_extremos.py` | Pico 2023–2025 (1 año vs 2 años) |
| `metodologia_correccion.txt` | Metodología (sin código) |
| `regiones.xlsx` | Lista de regiones |
| `leyenda_coleccion3.json` | Clases y colores LULC |

## Cómo correr

```bash
pip install -r requirements.txt
jupyter notebook Trayectorias_sos.ipynb
```

En config: `REGION_ID`, `MODO_CORRECCION` (`bosque` / `todas`) y `MAPA_ANOMALIAS` (`bosque` / `bosque_plantacion`). Ejecutar las celdas en orden.
