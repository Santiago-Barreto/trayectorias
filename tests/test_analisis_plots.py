from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

import analisis_nacional as an
from paths import TEST_FIGS as OUT
OUT.mkdir(parents=True, exist_ok=True)
TOTAL = 1_283_824_234


def _textos(fig) -> list[str]:
    out = []
    if fig._suptitle is not None and fig._suptitle.get_text():
        out.append(fig._suptitle.get_text())
    for ax in fig.axes:
        for t in (ax.get_title(), ax.get_xlabel(), ax.get_ylabel()):
            if t:
                out.append(t)
        out.extend(lb.get_text() for lb in ax.get_yticklabels() if lb.get_text())
        leg = ax.get_legend()
        if leg is not None:
            out.extend(t.get_text() for t in leg.get_texts())
            titulo = leg.get_title()
            if titulo is not None and titulo.get_text():
                out.append(titulo.get_text())
    return out


def _tiene_leyenda(ax) -> bool:
    return ax.get_legend() is not None


def _guardar(fig, name: str):
    textos = _textos(fig)
    assert textos, f'{name}: figura sin textos'
    path = OUT / f'{name}.png'
    fig.savefig(path, dpi=120, bbox_inches='tight')
    assert path.stat().st_size > 5_000, f'{name}: PNG demasiado pequeño'
    return textos


def test_cargar_csv():
    df = an.cargar_csv()
    assert {'region_id', 'year', 'trayectoria', 'tipo', 'pixeles'}.issubset(df.columns)
    assert 1986 <= df['year'].min() and df['year'].max() <= 2023
    print('OK cargar_csv', df.shape)


def test_nombres_clases():
    """Las etiquetas de ejes usan solo el código numérico."""
    assert an._label_tray('33-3-33-33', 'Bosque aislado 1 año') == '33-3-33-33'
    assert an._label_tray('21-3-3-21') == '21-3-3-21'
    assert '→' not in an._label_tray('21-3-3-21', 'Bosque aislado 2 años')
    print('OK etiquetas solo con código numérico')


def test_nacional_leyendas():
    df = an.cargar_csv()
    plt.close('all')
    res = an.analizar_nacional(df=df, total_colombia=TOTAL, show=False)
    figs = [plt.figure(n) for n in plt.get_fignums()]
    assert len(figs) == 4, f'nacional: esperaba 4 figuras, hay {len(figs)}'

    nombres = ['nac_01_resumen', 'nac_02_anual', 'nac_03_top', 'nac_04_concentracion']
    textos = []
    for fig, name in zip(figs, nombres):
        textos.extend(_guardar(fig, name))

    # Barras de tipo: los ejes deben nombrar la anomalía completa
    t_resumen = ' | '.join(_textos(figs[0]))
    assert 'Bosque aislado 1 año' in t_resumen, 'barras de tipo sin nombres completos'
    assert 'Píxeles anómalos' in t_resumen

    # Anual: ambos ejes con leyenda explicando izquierda/derecha
    ejes_anual = figs[1].axes
    assert any(_tiene_leyenda(ax) for ax in ejes_anual), 'gráfico anual sin leyenda'
    t_anual = ' | '.join(_textos(figs[1]))
    assert 'eje izquierdo' in t_anual and 'eje derecho' in t_anual
    assert 'Tipo de anomalía' in t_anual, 'barras anuales apiladas sin leyenda de tipo'

    # Top trayectorias: leyenda de tipos y códigos numéricos
    assert _tiene_leyenda(figs[2].axes[0]), 'top nacional sin leyenda'
    t_top = ' | '.join(_textos(figs[2]))
    assert '21-3-3-21' in t_top or any('-3-' in t for t in _textos(figs[2])), 'top nacional sin códigos'
    assert '→' not in t_top, 'top nacional no debe mostrar nombres de clase'

    # Concentración y extensión: leyenda en ambos paneles
    assert all(_tiene_leyenda(ax) for ax in figs[3].axes), 'panel sin leyenda'

    todos = [t for t in textos if t.startswith(('Nacional', 'Top 15', 'Evolución', 'Concentración', 'Extensión', 'Composición'))]
    assert len(todos) == len(set(todos)), f'títulos duplicados: {todos}'
    assert 'pct_colombia' in res['anual'].columns
    plt.close('all')
    print('OK nacional: 4 figuras con leyendas')


def test_regional_leyendas():
    df = an.cargar_csv()
    rid = df.groupby('region_id')['pixeles'].sum().idxmax()
    plt.close('all')
    res = an.analizar_region(rid, df=df, total_colombia=TOTAL, show=False)
    figs = [plt.figure(n) for n in plt.get_fignums()]
    assert len(figs) == 3, f'regional: esperaba 3 figuras (sin heatmap), hay {len(figs)}'

    nombres = [f'reg_{rid}_01_resumen', f'reg_{rid}_02_anual', f'reg_{rid}_03_patrones']
    textos = []
    for fig, name in zip(figs, nombres):
        textos.extend(_guardar(fig, name))
    joined = ' | '.join(textos)

    assert rid in joined, 'los títulos regionales deben nombrar la región'
    assert 'Concentración: ' not in joined, 'no debe repetirse la curva nacional'
    assert 'Extensión geográfica' not in joined, 'no debe repetirse el scatter nacional'
    assert 'heatmap' not in joined.lower() and 'Intensidad anual' not in joined

    assert any(_tiene_leyenda(ax) for ax in figs[1].axes), 'anual regional sin leyenda'
    t_anual = ' | '.join(_textos(figs[1]))
    assert 'píxeles anómalos del país' in t_anual

    # Patrones: leyenda de figura + códigos numéricos a la izquierda
    pat = figs[2]
    assert pat.legends or any(ax.get_legend() for ax in pat.axes), 'patrones sin leyenda'
    left_labels = [t.get_text() for t in pat.axes[0].get_yticklabels()]
    assert any('-3-' in t for t in left_labels), left_labels
    assert all('→' not in t for t in left_labels), 'no deben aparecer nombres de clase'
    assert 'pct_del_nacional' in res['anual'].columns
    plt.close('all')
    print('OK regional', rid, ': 3 figuras con leyendas')


def test_porcentajes_correctos():
    """El % regional se mide sobre píxeles anómalos, no sobre el área del país."""
    df = an.cargar_csv()
    rid = '30450'
    if rid not in set(df['region_id']):
        rid = str(df['region_id'].iloc[0])
    plt.close('all')
    res = an.analizar_region(rid, df=df, total_colombia=TOTAL, show=False)
    plt.close('all')

    total_nac = df['pixeles'].sum()
    total_reg = df[df['region_id'] == rid]['pixeles'].sum()
    esperado = 100 * total_reg / total_nac
    obtenido = 100 * res['patrones']['pixeles'].sum() / total_nac
    assert abs(esperado - obtenido) < 1e-6, f'peso regional mal calculado: {obtenido} vs {esperado}'

    # El % anual es región / nacional del mismo año, siempre <= 100
    anual = res['anual']
    assert (anual['pct_del_nacional'] <= 100).all()
    for _, r in anual.iterrows():
        ref = 100 * r['pixeles'] / r['pixeles_nac']
        assert abs(ref - r['pct_del_nacional']) < 1e-9

    peor = anual.loc[anual['pixeles'].idxmax()]
    print(f"OK porcentajes: region {rid} = {esperado:.2f}% de los anomalos del pais; "
          f"anio {int(peor['year'])} = {peor['pct_del_nacional']:.2f}%")


def test_tabla_formateada():
    """Las tablas deben mostrar el signo % para no confundir 0.69 con 69%."""
    df = pd.DataFrame({
        'year': [2023],
        'pixeles': [8451],
        'pct_del_nacional': [0.686350],
    })
    capturado = {}

    def fake_display(obj):
        capturado['obj'] = obj

    original = an.display
    an.display = fake_display
    try:
        an._tabla(
            df,
            {'year': 'Año', 'pixeles': 'Píxeles', 'pct_del_nacional': '% de los anómalos del país'},
            {'year': '{:.0f}', 'pixeles': '{:,.0f}', 'pct_del_nacional': '{:.2f}%'},
        )
    finally:
        an.display = original

    html = capturado['obj'].to_html()
    assert '0.69%' in html, f'el porcentaje debe llevar %: {html[:400]}'
    assert '8,451' in html
    assert '% de los anómalos del país' in html
    print('OK tabla con % explícito')


def test_figuras_no_se_acumulan():
    """Patrón del mapa: cada clic debe dejar una sola figura abierta."""
    def dibujar_como_el_mapa():
        plt.close('all')
        with plt.style.context('dark_background'):
            fig, ax = plt.subplots()
            ax.plot([1986, 1987], [3, 21])
        plt.close(fig)
        return fig

    for _ in range(5):
        dibujar_como_el_mapa()
    assert len(plt.get_fignums()) == 0, f'figuras acumuladas: {plt.get_fignums()}'

    # El estilo oscuro no debe filtrarse a los gráficos siguientes
    assert plt.rcParams['text.color'] not in ('white', '#ffffff'), 'dark_background se quedó activo'
    print('OK figuras no se acumulan y el estilo no se filtra')


def test_modos_distintos():
    df = an.cargar_csv()
    rid = df.groupby('region_id')['pixeles'].sum().idxmax()

    plt.close('all')
    an.analizar_nacional(df=df, total_colombia=TOTAL, show=False)
    nac = [t for n in plt.get_fignums() for t in _textos(plt.figure(n))]
    plt.close('all')
    an.analizar_region(rid, df=df, total_colombia=TOTAL, show=False)
    reg = [t for n in plt.get_fignums() for t in _textos(plt.figure(n))]
    plt.close('all')

    assert set(nac) != set(reg)
    assert any('Nacional' in t for t in nac)
    assert any(rid in t for t in reg)
    print('OK modos nacional y regional distintos')


if __name__ == '__main__':
    test_cargar_csv()
    test_nombres_clases()
    test_nacional_leyendas()
    test_regional_leyendas()
    test_porcentajes_correctos()
    test_tabla_formateada()
    test_figuras_no_se_acumulan()
    test_modos_distintos()
    print(f'\nFiguras en: {OUT}')
    print('TODAS LAS PRUEBAS OK')
