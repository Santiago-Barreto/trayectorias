# Trayectorias — falsos bosques MapBiomas Colombia

Detección y corrección de **bosque aislado** (clase LULC **3**) en la Colección 4 de MapBiomas Colombia. Un píxel clasificado como bosque debería persistir al menos **tres años consecutivos**; trayectorias con uno o dos años de bosque entre otras coberturas se consideran inconsistentes.

Proyecto GEE: `mapbiomas-colombia`  
Assets: `projects/mapbiomas-colombia/assets/LULC/COLECCION4/clasificacion-ft` (`COLOMBIA-{region_id}-{version}`)

## Contenido del repositorio

| Archivo | Descripción |
|---------|-------------|
| `Trayectorias_sos.ipynb` | Notebook principal: reglas, corrección, export masivo, EDA y mapa interactivo |
| `export_trayectorias_regiones.py` | Export batch de trayectorias imposibles a CSV (sin notebook) |
| `regiones.xlsx` | Lista de IDs de región (columna 1, sin encabezado) |
| `leyenda_coleccion3.json` | Nombres y paleta de clases LULC |
| `estadisticas_general_region.js` | Referencia GEE para estadísticas de área por clase (no integrado al flujo) |

## Requisitos

- Python 3.10+
- Cuenta en [Google Earth Engine](https://earthengine.google.com/) con acceso al proyecto `mapbiomas-colombia`
- Autenticación GEE: `earthengine authenticate`

```bash
pip install -r requirements.txt
```

## Uso rápido

### Notebook

1. Abrir `Trayectorias_sos.ipynb` y ejecutar las celdas en orden.
2. En **Configuración**, elegir modo:
   - `REGION_ID = None` → procesa todas las regiones del Excel y genera `trayectorias_imposibles_por_region.csv`
   - `REGION_ID = '30453'` → carga una región, aplica corrección y muestra mapa interactivo

Las reglas de detección y corrección están documentadas al inicio del notebook.

### Script de exportación

```bash
python export_trayectorias_regiones.py
```

Genera `trayectorias_imposibles_por_region.csv` con columnas `region_id`, `trayectoria` (p. ej. `33-3-33-33`), `tipo`, `pixeles`, etc.

## Anomalías detectadas

| Tipo | Patrón (4 años) |
|------|-----------------|
| Bosque aislado 1 año | `X → 3 → Y` con `X ≠ 3`, `Y ≠ 3` |
| Bosque aislado 2 años | `X → 3 → 3 → Y` con `X ≠ 3`, `Y ≠ 3` |

La corrección reemplaza el bosque falso según reglas de plantación (clases 9 y 35) y contexto temporal, en **dos pasadas** sobre la serie 1986–2023.

## Versión

**v1.0.0** — primera versión publicada: detección, corrección, export CSV y mapa exploratorio.

## Autor

Santiago Barreto — [GitHub](https://github.com/Santiago-Barreto/trayectorias)
