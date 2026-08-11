from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
import ast
import json

import pandas as pd

import estadisticas_correccion as ec


def test_groups_a_filas():
    rows = ec._groups_a_filas(2020, [{'class': 3, 'sum': 10.5}, {'class': 21, 'sum': 2}])
    assert rows == [
        {'year': 2020, 'clase': 3, 'ha': 10.5},
        {'year': 2020, 'clase': 21, 'ha': 2.0},
    ]
    assert ec._groups_a_filas(2000, None) == []
    print('OK groups_a_filas')


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
    assert 'ID03 · Bosque · Region X' in txt
    assert 'ID21 · Mosaico · Region X' in txt
    assert 'ORIGINAL ·' not in txt and 'CORREGIDA ·' not in txt
    assert '1,000.0' in txt and '1,010.0' in txt
    assert 'original' in txt and 'corregida' in txt and 'delta' in txt
    assert 'total' in txt
    assert '2,000.0' in txt and '2,020.0' in txt  # totales ID03
    assert '<table' not in txt
    assert txt.count('year') == 2  # un encabezado por clase
    print('OK texto anual por ID')


def test_resumen_y_plotly_offline():
    rows = []
    for y in (2000, 2001):
        rows.append({'year': y, 'clase': 3, 'nombre': 'Bosque', 'ha_original': 1000 + y, 'ha_corregida': 1010 + y, 'delta_ha': 10})
        rows.append({'year': y, 'clase': 21, 'nombre': 'Mosaico', 'ha_original': 500.0, 'ha_corregida': 490.0, 'delta_ha': -10})
    serie = pd.DataFrame(rows)
    resumen = ec.resumen_por_clase(serie)
    assert set(resumen['clase']) == {3, 21}
    assert 'delta_neto' in resumen.columns and 'delta_media' not in resumen.columns
    r3 = resumen.loc[resumen['clase'] == 3].iloc[0]
    assert abs(float(r3['delta_neto']) - 20.0) < 1e-9  # 10+10
    txt = ec.html_resumen(resumen, 'Region X')
    assert 'Bosque' in txt and 'Mosaico' in txt and 'delta_neto' in txt and '<table' not in txt
    fig = ec.fig_plotly_coberturas(serie, 'Region X')
    assert fig is not None and len(fig.data) >= 3
    print('OK resumen/plotly')


def test_csv_cache_upsert(tmp_path):
    rows = []
    for y in (2000, 2001):
        rows.append({
            'year': y, 'clase': 3, 'nombre': 'Bosque',
            'ha_original': 100.0, 'ha_corregida': 110.0, 'delta_ha': 10.0,
        })
    serie = pd.DataFrame(rows)
    path = tmp_path / 'coberturas.csv'
    ec.guardar_serie_csv(serie, path, region_id=30450)
    loaded = ec.serie_desde_csv(path, 30450)
    assert loaded is not None and len(loaded) == 2
    assert abs(float(loaded['ha_original'].sum()) - 200.0) < 1e-9

    # upsert otra región no borra la primera
    serie2 = serie.copy()
    serie2['ha_original'] = 50.0
    serie2['ha_corregida'] = 55.0
    serie2['delta_ha'] = 5.0
    ec.guardar_serie_csv(serie2, path, region_id=30102)
    all_df = pd.read_csv(path, encoding='utf-8-sig')
    assert set(all_df['region_id'].astype(str)) == {'30450', '30102'}

    # upsert misma región reemplaza
    serie3 = serie.copy()
    serie3['ha_original'] = 1.0
    serie3['ha_corregida'] = 2.0
    serie3['delta_ha'] = 1.0
    ec.guardar_serie_csv(serie3, path, region_id=30450)
    loaded2 = ec.serie_desde_csv(path, 30450)
    assert abs(float(loaded2['ha_original'].sum()) - 2.0) < 1e-9
    print('OK csv cache upsert')


def test_notebook_api():
    nb = json.loads((ROOT / 'Trayectorias_sos.ipynb').read_text(encoding='utf-8'))
    stats = ''
    cfg = ''
    for c in nb['cells']:
        s = ''.join(c.get('source', []))
        if 'estadisticas_correccion.calcular_y_mostrar' in s:
            stats = s
            ast.parse(s)
        if 'OUTPUT_CSV_STATS = CSV_COBERTURAS' in s:
            cfg = s
    assert 'STATS, FIG' in stats
    assert 'csv_path=OUTPUT_CSV_STATS' in stats
    assert 'forzar_recalculo=REEXPORTAR_STATS' in stats
    assert 'REEXPORTAR_STATS' in cfg
    assert 'CSV_COBERTURAS' in cfg
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
    from pathlib import Path as _P
    import tempfile

    test_groups_a_filas()
    test_extract_class3()
    test_html_anual()
    test_resumen_y_plotly_offline()
    test_csv_cache_upsert(_P(tempfile.mkdtemp()))
    test_notebook_api()
    test_match_export_id03_sample()
    print('TODAS OK')
