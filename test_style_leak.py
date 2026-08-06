"""Prueba: fugas de dark_background y etiquetas legibles."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import analisis_nacional as an

OUT = ROOT / '_test_figs'
OUT.mkdir(exist_ok=True)
TOTAL = 1_283_824_234


def _is_dark(color) -> bool:
    r, g, b = to_rgb(color)
    return (0.299 * r + 0.587 * g + 0.114 * b) < 0.55


def _textos_visibles(fig) -> list[str]:
    textos = []
    for ax in fig.axes:
        for t in (ax.get_title(), ax.get_xlabel(), ax.get_ylabel()):
            if t:
                textos.append(t)
        textos.extend(t.get_text() for t in ax.get_yticklabels() if t.get_text().strip())
        textos.extend(t.get_text() for t in ax.get_xticklabels() if t.get_text().strip())
        leg = ax.get_legend()
        if leg is not None:
            textos.extend(t.get_text() for t in leg.get_texts() if t.get_text().strip())
            titulo = leg.get_title()
            if titulo is not None and titulo.get_text().strip():
                textos.append(titulo.get_text())
    return textos


def test_style_resiste_dark_background():
    """Reproduce el bug: mapa deja dark_background y el análisis queda con texto blanco."""
    plt.style.use('dark_background')
    assert _is_dark(to_rgb('white')) is False
    # Tras dark_background el texto del rcParams es claro
    assert not _is_dark(plt.rcParams['text.color']), 'precondición: dark deja texto claro'

    df = an.cargar_csv()
    rid = '30450' if '30450' in set(df['region_id'].astype(str)) else str(df['region_id'].iloc[0])
    plt.close('all')
    an.analizar_region(rid, df=df, total_colombia=TOTAL, show=False)

    # _style() debe haber restaurado texto oscuro
    assert _is_dark(plt.rcParams['text.color']), (
        f"texto sigue claro tras análisis: {plt.rcParams['text.color']}"
    )
    assert _is_dark(plt.rcParams['axes.labelcolor'])
    assert plt.rcParams['figure.facecolor'] in ('white', '#ffffff', 'w')

    figs = [plt.figure(n) for n in plt.get_fignums()]
    assert len(figs) == 3
    for i, fig in enumerate(figs, 1):
        textos = _textos_visibles(fig)
        assert len(textos) >= 3, f'figura {i} sin textos visibles: {textos}'
        ylabels = [t.get_text() for ax in fig.axes for t in ax.get_yticklabels() if t.get_text().strip()]
        if i in (1, 3):  # resumen/tipos y patrones
            assert ylabels, f'figura {i} sin etiquetas Y (bug texto blanco/clipped)'
        path = OUT / f'leak_reg_{rid}_{i:02d}.png'
        fig.savefig(path, dpi=120, bbox_inches='tight', facecolor='white')
        assert path.stat().st_size > 8_000
    plt.close('all')
    plt.style.use('default')
    print('OK style resiste dark_background')


def test_barras_patrones_tienen_leyenda():
    df = an.cargar_csv()
    rid = df.groupby('region_id')['pixeles'].sum().idxmax()
    plt.close('all')
    an.analizar_region(rid, df=df, total_colombia=TOTAL, show=False)
    figs = [plt.figure(n) for n in plt.get_fignums()]
    assert len(figs) == 3

    pat = figs[2]
    assert pat.legends or any(ax.get_legend() for ax in pat.axes), 'patrones sin leyenda'
    left_labels = [t.get_text() for t in pat.axes[0].get_yticklabels()]
    assert any('-3-' in t for t in left_labels), left_labels
    assert all('→' not in t for t in left_labels)
    plt.close('all')
    print('OK barras de patrones con leyenda y códigos')


def test_pixel_plot_png_sin_fuga():
    """Simula el render del mapa: PNG claro y rcParams intactos."""
    plt.style.use('default')
    before = dict(plt.rcParams)

    df = __import__('pandas').DataFrame({'Año': list(range(1985, 2026)), 'Clase': [21, 3] * 20 + [21]})
    colors = ['#1f8d49' if c == 3 else '#ffefc3' for c in df['Clase']]
    fig, ax = plt.subplots(figsize=(10, 4), facecolor='white')
    ax.set_facecolor('#f7fafc')
    ax.plot(df['Año'], df['Clase'], color='#a0aec0')
    ax.scatter(df['Año'], df['Clase'], c=colors, s=40)
    ax.set_title('Trayectoria LULC · prueba', color='#1a202c')
    ax.set_xlabel('Año', color='#1a202c')
    ax.set_ylabel('Clase LULC', color='#1a202c')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, facecolor='white')
    plt.close(fig)
    assert len(buf.getvalue()) > 5_000

    # No debe haberse activado dark_background
    assert plt.rcParams['text.color'] == before['text.color'] or _is_dark(plt.rcParams['text.color'])
    print('OK pixel plot PNG sin fuga')


if __name__ == '__main__':
    test_style_resiste_dark_background()
    test_barras_patrones_tienen_leyenda()
    test_pixel_plot_png_sin_fuga()
    # Suite completa previa
    import test_analisis_plots as suite
    suite.test_cargar_csv()
    suite.test_nombres_clases()
    suite.test_nacional_leyendas()
    suite.test_regional_leyendas()
    suite.test_porcentajes_correctos()
    suite.test_tabla_formateada()
    suite.test_figuras_no_se_acumulan()
    suite.test_modos_distintos()
    print('\nTODAS LAS PRUEBAS OK')
