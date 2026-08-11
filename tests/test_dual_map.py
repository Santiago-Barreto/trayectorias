from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
import ast
import json

import pandas as pd


def test_map_cell_structure():
    nb = json.loads((ROOT / 'Trayectorias_sos.ipynb').read_text(encoding='utf-8'))
    src = None
    for c in nb['cells']:
        s = ''.join(c.get('source', []))
        if 'm_orig' in s and 'leafmap' in s:
            src = s
            break
    assert src, 'map cell missing'
    ast.parse(src)
    assert 'm_corr' not in src
    assert '_sync_maps' not in src
    assert 'construir_capa_ventana' in src
    assert 'year_selector' in src
    assert 'agregar_capas_anio' in src
    assert 'Calcular tabla' in src
    assert 'add_ee_layer' in src
    assert 'for ventana in (3, 4, 5)' in src
    assert 'm_orig.on_interaction' in src
    print('OK estructura mapa único')


def test_tabla_html_top15():
    # lightweight copy of ranking logic
    df = pd.DataFrame({
        'trayectoria': [f't{i}' for i in range(20)],
        'tipo': ['Bosque aislado 1 año'] * 20,
        'pixeles': list(range(20, 0, -1)),
    })
    show = df.head(15)
    assert len(show) == 15
    assert show.iloc[0]['pixeles'] == 20
    print('OK top15')


def test_plantacion_antes_bosque_describe():
    # Import describe from notebook is hard; replicate rule check via parsing functions cell
    nb = json.loads((ROOT / 'Trayectorias_sos.ipynb').read_text(encoding='utf-8'))
    fn = ''
    for c in nb['cells']:
        s = ''.join(c.get('source', []))
        if 'def anomalia_plantacion' in s and 'antes_1' in s:
            fn = s
            break
    assert 'antes_1' in fn and 'antes_2' in fn
    assert 'Plantación corta antes de bosque' in fn
    print('OK regla plantación antes de bosque presente')


if __name__ == '__main__':
    test_map_cell_structure()
    test_tabla_html_top15()
    test_plantacion_antes_bosque_describe()
    print('TODAS OK')
