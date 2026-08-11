from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
import ast
import json

import pandas as pd

import estadisticas_correccion as ec


def test_extract_class3():
    assert ec._ha_clase3_desde_groups([{'class': 21, 'sum': 10}, {'class': 3, 'sum': 55.5}]) == 55.5
    print('OK extract class3')


def test_html_anual():
    rows = []
    for y in (2000, 2001):
        rows.append({
            'year': y, 'clase': 3, 'nombre': 'Bosque',
            'ha_original': 1000.0, 'ha_corregida': 1010.0, 'delta_ha': 10.0,
        })
        rows.append({
            'year': y, 'clase': 21, 'nombre': 'Mosaico',
            'ha_original': 500.0, 'ha_corregida': 490.0, 'delta_ha': -10.0,
        })
    txt = ec.html_tabla_anual(pd.DataFrame(rows), 'Region X')
    assert 'ORIGINAL · ID03' in txt and 'CORREGIDA · ID03' in txt
    assert 'ORIGINAL · ID21' in txt and 'CORREGIDA · ID21' in txt
    assert '1,000.0' in txt and 'Bosque' in txt
    assert '<table' not in txt
    # cada bloque debe ser year + una sola columna ID
    assert txt.count('year') >= 4
    print('OK texto anual por ID')


def test_resumen_y_plotly_offline():
    rows = []
    for y in (2000, 2001):
        rows.append({'year': y, 'clase': 3, 'nombre': 'Bosque', 'ha_original': 1000 + y, 'ha_corregida': 1010 + y, 'delta_ha': 10})
        rows.append({'year': y, 'clase': 21, 'nombre': 'Mosaico', 'ha_original': 500.0, 'ha_corregida': 490.0, 'delta_ha': -10})
    serie = pd.DataFrame(rows)
    resumen = ec.resumen_por_clase(serie)
    assert set(resumen['clase']) == {3, 21}
    txt = ec.html_resumen(resumen, 'Region X')
    assert 'Bosque' in txt and 'Mosaico' in txt and '<table' not in txt
    fig = ec.fig_plotly_coberturas(serie, 'Region X')
    assert fig is not None and len(fig.data) >= 3
    print('OK resumen/plotly')


def test_notebook_api():
    nb = json.loads((ROOT / 'Trayectorias_sos.ipynb').read_text(encoding='utf-8'))
    stats = ''
    for c in nb['cells']:
        s = ''.join(c.get('source', []))
        if 'estadisticas_correccion.calcular_y_mostrar' in s:
            stats = s
            ast.parse(s)
    assert 'STATS, FIG' in stats
    assert 'pio.renderers.default' in stats
    assert 'class_names=CLASS_NAMES' in stats
    assert not stats.rstrip().endswith('FIG')
    print('OK notebook')


def test_match_export_id03_sample():
    import ee
    ee.Initialize(project='mapbiomas-colombia')
    img = ee.Image(
        'projects/mapbiomas-colombia/assets/LULC/COLECCION4/clasificacion-ft/COLOMBIA-30450-7'
    )
    geo = (
        ee.FeatureCollection(
            'projects/mapbiomas-colombia/assets/DATOS_AUXILIARES/VECTORES/'
            'clasificacion-regiones-3-buffer-250m'
        )
        .filter(ee.Filter.eq('id_regionC', 30450))
        .geometry()
    )
    ref = {1985: 73342.34114, 2020: 46575.62361}
    bands = [f'classification_{y}' for y in ref]
    df = ec.area_bosque_por_anio(img, bands, geometry=geo)
    for _, row in df.iterrows():
        y = int(row['year'])
        assert abs(float(row['ha']) - ref[y]) < 0.01, (y, row['ha'], ref[y])
    print('OK match ID03')


if __name__ == '__main__':
    test_extract_class3()
    test_html_anual()
    test_resumen_y_plotly_offline()
    test_notebook_api()
    test_match_export_id03_sample()
    print('TODAS OK')
