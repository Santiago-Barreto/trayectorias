"""Exporta trayectorias imposibles (bosque aislado) por región a un CSV unificado."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import ee
import pandas as pd

FOLDER = 'projects/mapbiomas-colombia/assets/LULC/COLECCION4/clasificacion-ft'
YEARS = ee.List.sequence(1986, 2023)
CLASE_BOSQUE = 3
GEE_PROJECT = 'mapbiomas-colombia'

BASE = Path(__file__).parent
LEYENDA_PATH = BASE / 'leyenda_coleccion3.json'
REGIONES_XLSX = BASE / 'regiones.xlsx'
OUTPUT_CSV = BASE / 'trayectorias_imposibles_por_region.csv'


def band_name(year):
    return ee.String('classification_').cat(ee.Number(year).format('%d'))


def load_class_names():
    with open(LEYENDA_PATH, encoding='utf-8') as f:
        data = json.load(f)
    return {int(k): v for k, v in data['class_names'].items()}


CLASS_NAMES = load_class_names()


def class_name(class_id):
    return CLASS_NAMES.get(int(class_id), f'Clase {int(class_id)}')


def anomalia_bosque(prev1, curr, next1, next2):
    error1 = prev1.neq(CLASE_BOSQUE).And(curr.eq(CLASE_BOSQUE)).And(next1.neq(CLASE_BOSQUE))
    error2_ini = prev1.neq(CLASE_BOSQUE).And(curr.eq(CLASE_BOSQUE)).And(next1.eq(CLASE_BOSQUE)).And(next2.neq(CLASE_BOSQUE))
    return error1.Or(error2_ini)


def describe_trayectoria(p1, c, n1, n2):
    p1, c, n1, n2 = map(int, (p1, c, n1, n2))
    if c != CLASE_BOSQUE:
        return 'Sin bosque aislado'
    if n1 != CLASE_BOSQUE and n2 != CLASE_BOSQUE:
        return 'Bosque aislado 1 año'
    if n1 == CLASE_BOSQUE and n2 != CLASE_BOSQUE:
        return 'Bosque aislado 2 años'
    return 'Revisar patrón'


def codigo_clases(p1, c, n1, n2):
    p1, c, n1, n2 = map(int, (p1, c, n1, n2))
    return f'{p1}-{c}-{n1}-{n2}'


def parse_trajectory(code, class_names=CLASS_NAMES):
    k = int(float(code))
    p1, c, n1, n2 = k // 1_000_000, (k % 1_000_000) // 10_000, (k % 10_000) // 100, k % 100
    ids = codigo_clases(p1, c, n1, n2)
    return {
        'codigo': k,
        'clase_1': p1, 'clase_2': c, 'clase_3': n1, 'clase_4': n2,
        'clases': ids,
        'trayectoria': ids,
        'tipo': describe_trayectoria(p1, c, n1, n2),
    }


def ids_desde_regiones(path: Path) -> list[str]:
    """Lee IDs de región desde la primera columna del xlsx (sin encabezado), en orden del archivo."""
    col = pd.read_excel(path, header=None, usecols=[0]).iloc[:, 0].dropna()
    ids = col.astype(int).astype(str).drop_duplicates().tolist()
    if not ids:
        raise ValueError(f'No se encontraron IDs de región en {path}')
    return ids


def cargar_asset_region(region_id: str, folder: str = FOLDER):
    """Busca COLOMBIA-{region_id}-{version} en GEE; region_id viene del Excel."""
    rid = str(region_id).strip()
    prefix = f'COLOMBIA-{rid}-'
    assets = ee.data.listAssets({'parent': folder})['assets']
    matches = []
    for a in assets:
        base = a['name'].split('/')[-1]
        if not base.startswith(prefix):
            continue
        ver = base[len(prefix):]
        if ver.isdigit() and int(ver) != 11:
            matches.append(a)
    matches = sorted(matches, key=lambda a: int(a['name'].split('/')[-1].rsplit('-', 1)[-1]), reverse=True)
    if not matches:
        return None, None
    name = matches[0]['name']
    return ee.Image(name), name


def histograma_trayectorias(imagen):
    def mapear_anomalias(y):
        year = ee.Number(y)
        prev1 = imagen.select(band_name(year.subtract(1)))
        curr = imagen.select(band_name(year))
        next1 = imagen.select(band_name(year.add(1)))
        next2 = imagen.select(band_name(year.add(2)))
        anomalia = anomalia_bosque(prev1, curr, next1, next2)
        trayectoria = prev1.multiply(1_000_000).add(curr.multiply(10_000)).add(next1.multiply(100)).add(next2)
        return ee.Image([anomalia.rename('error'), trayectoria.updateMask(anomalia).rename('trajectory')])

    errores = ee.ImageCollection.fromImages(YEARS.map(mapear_anomalias))
    trajectories_img = errores.select('trajectory').max()
    hist = trajectories_img.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=imagen.geometry(),
        scale=30,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()
    return hist.get('trajectory') or {}


def main():
    if not REGIONES_XLSX.exists():
        print(f'No existe {REGIONES_XLSX}', file=sys.stderr)
        sys.exit(1)

    ee.Initialize(project=GEE_PROJECT)
    region_ids = ids_desde_regiones(REGIONES_XLSX)
    print(f'Regiones en Excel: {len(region_ids)}')

    filas = []
    omitidas = 0
    sin_anomalias = 0

    for i, rid in enumerate(region_ids, 1):
        print(f'[{i}/{len(region_ids)}] {rid}...', end=' ', flush=True)
        try:
            img, asset = cargar_asset_region(rid)
        except Exception as err:
            print(f'error ({err})')
            omitidas += 1
            continue
        if img is None:
            print('sin asset')
            omitidas += 1
            continue
        try:
            hist = histograma_trayectorias(img)
        except Exception as err:
            print(f'error GEE ({err})')
            omitidas += 1
            continue
        if not hist:
            print('sin anomalías')
            sin_anomalias += 1
            continue
        for codigo, pixeles in hist.items():
            filas.append({
                'region_id': rid,
                'asset': asset,
                **parse_trajectory(codigo),
                'pixeles': int(pixeles),
            })
        print(f'{len(hist)} patrones')

    df = pd.DataFrame(filas).sort_values(['region_id', 'pixeles'], ascending=[True, False])
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f'\nGuardado: {OUTPUT_CSV}')
    print(f'Filas: {len(df):,} · Omitidas: {omitidas} · Sin anomalías: {sin_anomalias}')


if __name__ == '__main__':
    main()
