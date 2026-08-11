from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
import ee

import estadisticas_correccion as ec

ASSET = "projects/mapbiomas-colombia/assets/LULC/COLECCION4/clasificacion-ft/COLOMBIA-30450-7"
VECTOR_BAD = (
    "projects/mapbiomas-colombia/assets/DATOS_AUXILIARES/VECTORES/"
    "clasificacion-regiones-5-buffer-250m"
)
VECTOR_OK = (
    "projects/mapbiomas-colombia/assets/DATOS_AUXILIARES/VECTORES/"
    "clasificacion-regiones-3-buffer-250m"
)


def _ha_group(img, band, geometry) -> float:
    img_year = img.select(band).int16().selfMask()
    area_img = ee.Image.pixelArea().divide(1e4).addBands(img_year)
    groups = area_img.reduceRegion(
        reducer=ee.Reducer.sum().group(groupField=1, groupName="class"),
        geometry=geometry,
        scale=30,
        maxPixels=1e13,
        bestEffort=True,
    ).get("groups").getInfo()
    return ec._ha_clase3_desde_groups(groups)


def test_roi_c5_sin_overlap():
    ee.Initialize(project="mapbiomas-colombia")
    img = ee.Image(ASSET)
    geo_bad = (
        ee.FeatureCollection(VECTOR_BAD)
        .filter(ee.Filter.eq("id_regionC", 30450))
        .geometry()
    )
    inter = geo_bad.intersection(img.geometry(), 1).area(1).getInfo()
    assert inter == 0 or inter < 1, inter
    ha = _ha_group(img, "classification_2020", geo_bad)
    assert ha == 0.0
    print("OK ROI C5 sin overlap -> 0 ha")


def test_huella_asset_no_cero():
    ee.Initialize(project="mapbiomas-colombia")
    img = ee.Image(ASSET)
    ha = _ha_group(img, "classification_2020", img.geometry())
    assert ha > 1000, ha
    print(f"OK huella asset 2020 = {ha:,.1f} ha")


def test_modulo_un_anio():
    ee.Initialize(project="mapbiomas-colombia")
    img = ee.Image(ASSET)
    df = ec.area_bosque_por_anio(
        img, ["classification_2020"], geometry=img.geometry(), scale=30,
    )
    assert len(df) == 1
    assert float(df.iloc[0]["ha"]) > 1000
    print(f"OK modulo area_bosque_por_anio = {df.iloc[0]['ha']:,.1f} ha")


def test_vector_c3_overlap():
    ee.Initialize(project="mapbiomas-colombia")
    img = ee.Image(ASSET)
    geo = (
        ee.FeatureCollection(VECTOR_OK)
        .filter(ee.Filter.eq("id_regionC", 30450))
        .geometry()
    )
    inter = geo.intersection(img.geometry(), 1).area(1).getInfo()
    assert inter > 1e6, inter
    ha = _ha_group(img, "classification_2020", geo)
    assert ha > 0, ha
    print(f"OK ROI C3 overlap · 2020 = {ha:,.1f} ha")


if __name__ == "__main__":
    test_roi_c5_sin_overlap()
    test_huella_asset_no_cero()
    test_modulo_un_anio()
    test_vector_c3_overlap()
    print("TODAS OK")
