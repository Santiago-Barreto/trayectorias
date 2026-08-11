from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
import ast
import json


def _map_src():
    nb = json.loads((ROOT / 'Trayectorias_sos.ipynb').read_text(encoding='utf-8'))
    src = None
    for c in nb['cells']:
        s = ''.join(c.get('source', []))
        if 'm_orig' in s and 'leafmap' in s and 'construir_capas_anio' in s:
            src = s
            break
    return src


def test_map_cell_structure():
    src = _map_src()
    assert src, 'map cell missing'
    assert 'm_corr_map' not in src
    ast.parse(src)
    assert 'construir_capas_anio' in src
    assert 'construir_capas_general' in src
    assert 'construir_capa_ventana' not in src
    assert 'construir_trayectorias_anio' not in src
    assert 'vista_selector' in src
    assert 'year_selector' in src
    assert 'agregar_capas_anio' in src
    assert '_capas_para_vista' in src
    assert 'Mostrar tablas' in src
    assert src.count('mapa.add_ee_layer') == 1
    assert "LAYER_NAMES = ['bosque', 'resto']" in src
    assert 'm_orig.on_interaction' in src
    assert 'agregar_capas_anio(m_orig, IMG_ORIGINAL' in src
    print('OK estructura mapa')


def test_tablas_antes_despues_general_anual():
    src = _map_src()
    assert 'table_vista' in src
    assert 'table_html_orig' in src and 'table_html_corr' in src
    assert 'agregar_patrones_local' in src
    assert 'DF_PATRONES_ORIG' in src and 'DF_PATRONES_CORR' in src
    nb = json.loads((ROOT / 'Trayectorias_sos.ipynb').read_text(encoding='utf-8'))
    load = ''
    for c in nb['cells']:
        s = ''.join(c.get('source', []))
        if 'DF_PATRONES_ORIG = df_patrones_desde_hist' in s:
            load = s
            break
    assert load and 'histogramas_trayectorias_por_anio' in load
    print('OK tablas locales orig+corr')


def test_html_tabla_top5_en_mapa():
    src = _map_src()
    assert 'df.head(5)' in src
    assert 'top 5' in src.lower()
    print('OK top5 en mapa')


if __name__ == '__main__':
    test_map_cell_structure()
    test_tablas_antes_despues_general_anual()
    test_html_tabla_top5_en_mapa()
    print('TODAS OK')
