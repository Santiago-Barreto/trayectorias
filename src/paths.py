from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
OUTPUTS = ROOT / 'outputs'
SRC = ROOT / 'src'

LEYENDA = DATA / 'leyenda_coleccion3.json'
REGIONES = DATA / 'regiones.xlsx'
CSV_ANOMALIAS = OUTPUTS / 'trayectorias_imposibles_por_region.csv'
TEST_FIGS = OUTPUTS / 'test_figs'

OUTPUTS.mkdir(exist_ok=True)
