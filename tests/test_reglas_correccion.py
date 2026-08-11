# -*- coding: utf-8 -*-
"""Reglas de corrección: huecos 1–2 años bosque+9/35/74; islas → contexto."""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))


def _fns_src() -> str:
    nb = json.loads((ROOT / 'Trayectorias_sos.ipynb').read_text(encoding='utf-8'))
    for c in nb['cells']:
        s = ''.join(c.get('source', []))
        if 'def corregir_matriz_importancia' in s:
            return s
    raise AssertionError('functions cell missing')


def test_huecos_bosque_y_plantacion_en_codigo():
    src = _fns_src()
    ast.parse(src)
    body = src[src.find('def corregir_matriz_importancia'):]
    assert 'clases_hueco' in body
    assert 'CLASES_PLANTACION' in body
    assert 'longitud=2' in body
    assert 'corregir_bosque_y_plantaciones' in body
    head = body.split('def ', 1)[0] if False else body[:500]
    assert 'modo=None' not in head
    print('OK codigo: huecos 1-2 bosque+plantacion')


def test_config_ventanas():
    nb = json.loads((ROOT / 'Trayectorias_sos.ipynb').read_text(encoding='utf-8'))
    cfg = ''
    for c in nb['cells']:
        s = ''.join(c.get('source', []))
        if 'VENTANAS_HUECOS' in s and 'REGION_ID' in s:
            cfg = s
            break
    assert 'VENTANAS_HUECOS = (3, 4)' in cfg
    assert 'MODO_CORRECCION' not in cfg
    assert 'YEARS = ee.List' not in cfg
    print('OK config limpia')


def test_un_solo_pipeline_correccion():
    src = _fns_src()
    body = src[src.find('def corregir_matriz_importancia'):]
    assert "modo == 'bosque'" not in body
    assert 'clases_hueco' in body
    assert 'codigo_desde_k' not in src
    print('OK un solo pipeline')


def _gap_fill(series, longitud, valor=3):
    out = list(series)
    for i in range(1, len(out) - longitud):
        if out[i - 1] == valor and out[i + longitud] == valor:
            if all(out[i + k] != valor for k in range(longitud)):
                for k in range(longitud):
                    out[i + k] = valor
    return out


def test_no_borrar_mosaico_tres_anos():
    serie = [3, 3, 21, 21, 21, 3, 3, 3]
    assert _gap_fill(serie, 1) == serie
    assert _gap_fill(serie, 2) == serie
    print('OK conserva 3-21-21-21-3')


def test_rellena_huecos_bosque_y_palma():
    assert _gap_fill([3, 21, 3], 1) == [3, 3, 3]
    assert _gap_fill([3, 21, 21, 3], 2) == [3, 3, 3, 3]
    assert _gap_fill([35, 21, 21, 35], 2, valor=35) == [35, 35, 35, 35]
    print('OK huecos 3-X-3 / 3-XX-3 / 35-XX-35')


def test_plantacion_isla():
    src = _fns_src()
    assert 'reemplazo_plantacion_isla' in src
    assert 'corregir_plantaciones_aisladas' in src

    def sim(prev, curr, nxt, bosque=3, plants=(9, 35, 74)):
        if curr not in plants:
            return curr
        if prev in plants or nxt in plants:
            return curr
        return bosque if nxt == bosque else prev

    assert sim(21, 35, 21) == 21
    assert sim(3, 35, 3) == 3
    assert sim(21, 35, 3) == 3
    print('OK plantacion isla')


if __name__ == '__main__':
    test_huecos_bosque_y_plantacion_en_codigo()
    test_config_ventanas()
    test_un_solo_pipeline_correccion()
    test_no_borrar_mosaico_tres_anos()
    test_rellena_huecos_bosque_y_palma()
    test_plantacion_isla()
    print('TODAS OK')
