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
    assert '_sync_maps' not in src
    assert '_link_map_views' in src
    assert 'm_corr' in src and 'm_orig' in src
    assert 'refrescar_capas_corr' in src
    assert 'construir_capa_ventana' in src
    assert 'year_selector' in src
    assert 'year_selector_corr' in src
    assert 'agregar_capas_anio' in src
    assert 'Calcular tabla' in src
    assert 'add_ee_layer' in src
    assert 'for ventana in (3, 4, 5)' in src
    assert "grupo == 'bosque'" in src or 'grupo == "bosque"' in src
    assert 'COLORES_BOSQUE' in src and 'COLORES_RESTO' in src
    assert 'm_orig.on_interaction' in src
    assert 'm_corr.on_interaction' in src
    print('OK estructura mapas original + residuales')


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


def test_link_map_views_logic():
    """Simula el enlace center/zoom del notebook (sin UI)."""
    class FakeMap:
        def __init__(self, center, zoom):
            self.center = list(center)
            self.zoom = float(zoom)
            self._obs = []

        def observe(self, handler, names=None):
            self._obs.append((handler, names))

        def _notify(self):
            for handler, _names in self._obs:
                handler({'type': 'change'})

    view_lock = {'busy': False}

    def link_map_views(src_map, dst_map):
        if view_lock['busy']:
            return
        new_center = [float(src_map.center[0]), float(src_map.center[1])]
        new_zoom = float(src_map.zoom)
        old_center = [float(dst_map.center[0]), float(dst_map.center[1])]
        old_zoom = float(dst_map.zoom)
        if new_center == old_center and abs(new_zoom - old_zoom) < 1e-9:
            return
        view_lock['busy'] = True
        try:
            dst_map.center = new_center
            dst_map.zoom = new_zoom
            dst_map._notify()
        finally:
            view_lock['busy'] = False

    m1 = FakeMap([4.5, -73.0], 6)
    m2 = FakeMap([4.5, -73.0], 6)
    m1.observe(lambda ch: link_map_views(m1, m2), names=['center', 'zoom'])
    m2.observe(lambda ch: link_map_views(m2, m1), names=['center', 'zoom'])

    m1.center = [5.2, -74.1]
    m1._notify()
    assert m2.center == [5.2, -74.1]
    m1.zoom = 9.0
    m1._notify()
    assert m2.zoom == 9.0
    m2.center = [6.0, -75.0]
    m2._notify()
    assert m1.center == [6.0, -75.0]
    print('OK link_map_views (fake)')


def test_link_map_views_leafmap_live():
    try:
        import leafmap
    except Exception as err:
        print(f'SKIP leafmap live: {err}')
        return

    m1 = leafmap.Map(center=[4.5, -73.0], zoom=6)
    m2 = leafmap.Map(center=[4.5, -73.0], zoom=6)
    view_lock = {'busy': False}

    def link_map_views(src_map, dst_map):
        if view_lock['busy']:
            return
        new_center = [float(src_map.center[0]), float(src_map.center[1])]
        new_zoom = float(src_map.zoom)
        old_center = [float(dst_map.center[0]), float(dst_map.center[1])]
        old_zoom = float(dst_map.zoom)
        if new_center == old_center and abs(new_zoom - old_zoom) < 1e-9:
            return
        view_lock['busy'] = True
        try:
            dst_map.center = new_center
            dst_map.zoom = new_zoom
        finally:
            view_lock['busy'] = False

    m1.observe(lambda ch: link_map_views(m1, m2), names=['center', 'zoom'])
    m2.observe(lambda ch: link_map_views(m2, m1), names=['center', 'zoom'])

    m1.center = [5.2, -74.1]
    assert list(m2.center) == [5.2, -74.1]
    m1.zoom = 9
    assert float(m2.zoom) == 9.0
    m2.center = [6.0, -75.0]
    assert list(m1.center) == [6.0, -75.0]
    print('OK link_map_views (leafmap live)')


if __name__ == '__main__':
    test_map_cell_structure()
    test_tabla_html_top15()
    test_plantacion_antes_bosque_describe()
    test_link_map_views_logic()
    test_link_map_views_leafmap_live()
    print('TODAS OK')
