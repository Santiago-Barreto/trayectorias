"""Análisis de trayectorias imposibles: modo nacional o por región."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from IPython.display import display

CSV_REGION = Path('trayectorias_imposibles_por_region.csv')
LEYENDA_PATH = Path('leyenda_coleccion3.json')
TOTAL_COLOMBIA_DEFAULT = 1_283_824_234

COLOR_1A = '#2b6cb0'
COLOR_2A = '#c05621'
COLOR_REV = '#718096'
COLOR_REG = '#319795'
COLOR_PESO = '#805ad5'
TIPO_COLOR = {
    'Bosque aislado 1 año': COLOR_1A,
    'Bosque aislado 2 años': COLOR_2A,
    'Revisar patrón': COLOR_REV,
}
TIPO_SHORT = {
    'Bosque aislado 1 año': '1 año',
    'Bosque aislado 2 años': '2 años',
    'Revisar patrón': 'Revisar',
}
TIPO_ORDEN = ['Bosque aislado 1 año', 'Bosque aislado 2 años', 'Revisar patrón']

# Abreviaturas legibles para las clases más frecuentes en las trayectorias.
ABREV_CLASES = {
    3: 'Bosque', 5: 'Manglar', 6: 'Bosq.inund', 9: 'Silvic.', 11: 'Inundable',
    12: 'Herbácea', 13: 'Otra NF', 21: 'Mosaico', 23: 'Playa', 24: 'Urbano',
    25: 'Sin veg.', 29: 'Roca', 30: 'Minería', 31: 'Acuicult.', 32: 'Marea',
    33: 'Agua', 34: 'Glaciar', 35: 'Palma', 49: 'Leñosa/ar', 50: 'Herb./ar',
    68: 'Nat.sinveg', 74: 'Banano', 75: 'Solar', 81: 'Andina', 82: 'Andina.in',
}


def _cargar_nombres_clases() -> dict[int, str]:
    if not LEYENDA_PATH.exists():
        return {}
    data = json.loads(LEYENDA_PATH.read_text(encoding='utf-8'))
    salida = {}
    for k, v in data.get('class_names', {}).items():
        nombre = str(v)
        if '. ' in nombre:
            nombre = nombre.split('. ', 1)[1]
        salida[int(k)] = nombre
    return salida


CLASS_NAMES = _cargar_nombres_clases()


def _abrev(cid: int) -> str:
    if cid in ABREV_CLASES:
        return ABREV_CLASES[cid]
    nombre = CLASS_NAMES.get(cid, str(cid))
    return nombre[:10]


def _nombres_trayectoria(tray: str) -> str:
    try:
        partes = [int(p) for p in str(tray).split('-')]
    except ValueError:
        return ''
    return '→'.join(_abrev(p) for p in partes)


def _style():
    """Fuerza tema claro. Evita texto blanco si el mapa dejó dark_background activo."""
    plt.style.use('default')
    plt.rcParams.update({
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'savefig.facecolor': 'white',
        'axes.edgecolor': '#cbd5e0',
        'axes.grid': True,
        'grid.color': '#edf2f7',
        'grid.linewidth': 0.8,
        'axes.axisbelow': True,
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
        'figure.titlesize': 13,
        'text.color': '#1a202c',
        'axes.labelcolor': '#1a202c',
        'axes.titlecolor': '#1a202c',
        'xtick.color': '#4a5568',
        'ytick.color': '#4a5568',
        'legend.facecolor': 'white',
        'legend.edgecolor': '#cbd5e0',
        'legend.labelcolor': '#1a202c',
        'legend.fontsize': 8.5,
        'legend.title_fontsize': 9,
    })
    plt.close('all')


def _pintar_leyenda(leg):
    if leg is None:
        return
    frame = leg.get_frame()
    frame.set_facecolor('white')
    frame.set_edgecolor('#cbd5e0')
    frame.set_alpha(0.95)
    for t in leg.get_texts():
        t.set_color('#1a202c')
    title = leg.get_title()
    if title is not None and title.get_text():
        title.set_color('#1a202c')


def _aplicar_texto_oscuro(fig):
    """Garantiza texto/leyendas negros aunque haya fuga de estilo oscuro."""
    ink, muted = '#1a202c', '#4a5568'
    fig.patch.set_facecolor('white')
    for ax in fig.axes:
        ax.set_facecolor('white')
        ax.title.set_color(ink)
        ax.xaxis.label.set_color(ink)
        ax.yaxis.label.set_color(ink)
        ax.tick_params(axis='x', labelcolor=muted, color=muted)
        ax.tick_params(axis='y', labelcolor=muted, color=muted)
        for spine in ax.spines.values():
            spine.set_color('#cbd5e0')
        _pintar_leyenda(ax.get_legend())
    for leg in getattr(fig, 'legends', []):
        _pintar_leyenda(leg)
    if getattr(fig, '_suptitle', None) is not None:
        fig._suptitle.set_color(ink)


def _mostrar(fig, show: bool):
    _aplicar_texto_oscuro(fig)
    if show:
        plt.show()


def _fmt_k(x, _pos=None):
    if abs(x) >= 1_000_000:
        return f'{x / 1_000_000:.1f}M'
    if abs(x) >= 1_000:
        return f'{x / 1_000:.0f}k'
    return f'{int(x)}'


def _label_tray(tray: str, tipo: str | None = None) -> str:
    """Etiqueta solo con el código numérico de la trayectoria."""
    return str(tray)


def _anotar_pico(ax, pico, years):
    """Anota el año pico hacia el lado con espacio disponible."""
    al_final = pico['year'] >= years.max() - (years.max() - years.min()) * 0.15
    dx, ha = (-12, 'right') if al_final else (10, 'left')
    ax.annotate(
        f"Pico {int(pico['year'])}\n{int(pico['pixeles']):,} px",
        (pico['year'], pico['pixeles']),
        xytext=(dx, 12), textcoords='offset points',
        ha=ha, color=COLOR_2A, fontsize=9,
    )


def _leyenda_tipos(ax, loc='lower right', titulo='Tipo de anomalía'):
    handles = [mpatches.Patch(color=TIPO_COLOR[t], label=f'{TIPO_SHORT[t]} — {t}') for t in TIPO_ORDEN]
    ax.legend(handles=handles, loc=loc, fontsize=8.5, title=titulo, title_fontsize=9, framealpha=0.95)


def _ensure_trayectoria(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if 'trayectoria' not in out.columns:
        if 'clases' in out.columns:
            out['trayectoria'] = out['clases']
        elif 'codigo' in out.columns:
            def _cod(k):
                k = int(float(k))
                return f'{k // 1_000_000}-{(k % 1_000_000) // 10_000}-{(k % 10_000) // 100}-{k % 100}'
            out['trayectoria'] = out['codigo'].apply(_cod)
    out['region_id'] = out['region_id'].astype(str)
    return out


def cargar_csv(path: Path | str | None = None) -> pd.DataFrame:
    csv_path = Path(path) if path else CSV_REGION
    if not csv_path.exists():
        raise FileNotFoundError(f'Necesitas {csv_path.name} en la carpeta del proyecto.')
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    if 'year' not in df.columns:
        raise ValueError(f'{csv_path.name} no tiene columna year. Regenera el CSV con REEXPORTAR=True.')
    return _ensure_trayectoria(df)


def agregar_patrones(df: pd.DataFrame) -> pd.DataFrame:
    keys = [c for c in ['codigo', 'trayectoria', 'tipo', 'clase_1', 'clase_2', 'clase_3', 'clase_4'] if c in df.columns]
    out = (
        df.groupby(keys, as_index=False)
        .agg(pixeles=('pixeles', 'sum'), n_regiones=('region_id', 'nunique'), n_anios=('year', 'nunique'))
        .sort_values('pixeles', ascending=False)
        .reset_index(drop=True)
    )
    total = out['pixeles'].sum()
    out['pct_pixeles'] = (100 * out['pixeles'] / total).round(4) if total else 0.0
    return out


def serie_anual(df: pd.DataFrame, total_colombia: int | None = None) -> pd.DataFrame:
    anual = (
        df.groupby('year', as_index=False)
        .agg(pixeles=('pixeles', 'sum'), n_regiones=('region_id', 'nunique'), n_patrones=('codigo', 'nunique'))
        .sort_values('year')
    )
    if total_colombia:
        anual['pct_colombia'] = 100 * anual['pixeles'] / total_colombia
    return anual


def serie_anual_tipo(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(['year', 'tipo'], as_index=False)['pixeles']
        .sum()
        .sort_values(['year', 'tipo'])
    )


def _tabla(df: pd.DataFrame, columnas: dict[str, str], formatos: dict | None = None, n: int = 15):
    """Muestra una tabla con nombres de columna explícitos y valores ya formateados."""
    use = [c for c in columnas if c in df.columns]
    view = df[use].head(n).copy()
    for col, fmt in (formatos or {}).items():
        if col in view.columns:
            view[col] = view[col].map(lambda v: fmt.format(v) if pd.notna(v) else '—')
    view = view.rename(columns={c: columnas[c] for c in use})
    try:
        display(view.style.hide(axis='index'))
    except Exception:
        print(view.to_string(index=False))


def _plot_tipo_barras(ax, por_tipo: pd.DataFrame, total_px: int, titulo: str):
    y = np.arange(len(por_tipo))
    colors = [TIPO_COLOR.get(t, '#a0aec0') for t in por_tipo['tipo']]
    ax.barh(y, por_tipo['pixeles'], color=colors, height=0.65, edgecolor='white')
    ax.set_yticks(y, list(por_tipo['tipo']), fontsize=9)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    ax.set_xlabel('Píxeles anómalos')
    ax.set_ylabel('Tipo de anomalía')
    ax.set_title(titulo)
    for i, (_, r) in enumerate(por_tipo.iterrows()):
        pct = 100 * r['pixeles'] / total_px if total_px else 0
        ax.text(r['pixeles'], i, f"  {int(r['pixeles']):,}  ({pct:.1f}%)",
                va='center', fontsize=9, color='#2d3748')
    ax.set_xlim(0, por_tipo['pixeles'].max() * 1.42)


def _plot_kpis(ax, items: list[tuple[str, str]], titulo: str):
    ax.axis('off')
    ax.set_title(titulo, loc='left', pad=8)
    for i, (lab, val) in enumerate(items):
        y = 0.94 - i * 0.155
        ax.text(0.02, y, lab, fontsize=9.5, color='#718096', transform=ax.transAxes, va='top')
        ax.text(0.02, y - 0.058, val, fontsize=13.5, fontweight='bold', color='#1a202c',
                transform=ax.transAxes, va='top', family='monospace')


def _plot_anual_tipo(ax, anual_tipo: pd.DataFrame, titulo: str, xlabel: str):
    years = sorted(anual_tipo['year'].unique())
    bottom = np.zeros(len(years))
    for tipo in TIPO_ORDEN:
        vals = (
            anual_tipo[anual_tipo['tipo'] == tipo]
            .set_index('year').reindex(years)['pixeles'].fillna(0).values
        )
        ax.bar(years, vals, bottom=bottom, color=TIPO_COLOR[tipo], width=0.85,
               label=f'{TIPO_SHORT[tipo]} — {tipo}', edgecolor='white', linewidth=0.3)
        bottom += vals
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    ax.set_xlabel(xlabel)
    ax.set_ylabel('Píxeles anómalos')
    ax.set_title(titulo)
    ax.legend(loc='upper left', fontsize=8.5, title='Tipo de anomalía', title_fontsize=9, framealpha=0.95)


def analizar_nacional(
    df: pd.DataFrame | None = None,
    total_colombia: int = TOTAL_COLOMBIA_DEFAULT,
    show: bool = True,
):
    """Análisis agregado de todas las regiones (sin filtro REGION_ID)."""
    _style()
    src = cargar_csv() if df is None else _ensure_trayectoria(df)
    df_nac = agregar_patrones(src)
    total_px = int(df_nac['pixeles'].sum())
    n_pat = len(df_nac)
    n_reg = src['region_id'].nunique()
    cum = df_nac['pixeles'].cumsum() / total_px
    n80 = int(np.searchsorted(cum.values, 0.8) + 1)
    n95 = int(np.searchsorted(cum.values, 0.95) + 1)
    por_tipo = (
        df_nac.groupby('tipo', as_index=False)['pixeles']
        .sum()
        .sort_values('pixeles', ascending=False)
    )
    anual = serie_anual(src, total_colombia=total_colombia)
    anual_tipo = serie_anual_tipo(src)
    pico = anual.loc[anual['pixeles'].idxmax()]

    print('=== Analisis NACIONAL ===')
    print(f'  Regiones con datos:  {n_reg}')
    print(f'  Patrones distintos:  {n_pat:,}')
    print(f'  Pixeles anomalos:    {total_px:,}  ({100 * total_px / total_colombia:.3f}% del area de Colombia)')
    print(f'  Patron dominante:    {df_nac.iloc[0]["trayectoria"]} ({df_nac.iloc[0]["pct_pixeles"]:.1f}% de los anomalos)')
    print(f'  Patrones ~80% / 95%: {n80} / {n95}')
    print(f'  Anio pico:           {int(pico["year"])} -> {int(pico["pixeles"]):,} px ({pico["pct_colombia"]:.3f}% del area de Colombia)')

    # 1. KPIs + composición por tipo
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8), gridspec_kw={'width_ratios': [1.05, 1.25]})
    _plot_kpis(axes[0], [
        ('Regiones con datos', f'{n_reg}'),
        ('Patrones distintos', f'{n_pat:,}'),
        ('Píxeles anómalos', f'{total_px:,}'),
        ('% del área de Colombia', f'{100 * total_px / total_colombia:.3f}%'),
        ('Patrón dominante', str(df_nac.iloc[0]['trayectoria'])),
        ('Patrones ≈80% / 95%', f'{n80} / {n95}'),
    ], 'Indicadores nacionales')
    _plot_tipo_barras(axes[1], por_tipo, total_px, 'Composición por tipo de anomalía')
    fig.suptitle('Nacional — resumen', y=1.02)
    fig.tight_layout()
    _mostrar(fig, show)

    # 2. Análisis anual
    fig, axes = plt.subplots(2, 1, figsize=(13, 8.6), sharex=True, gridspec_kw={'height_ratios': [1.1, 1]})
    ax = axes[0]
    ax.fill_between(anual['year'], anual['pixeles'], color=COLOR_1A, alpha=0.15)
    ax.plot(anual['year'], anual['pixeles'], color=COLOR_1A, lw=2.2, marker='o', ms=3.5,
            label='Píxeles anómalos (eje izquierdo)')
    ax.scatter([pico['year']], [pico['pixeles']], color=COLOR_2A, zorder=3, s=55)
    _anotar_pico(ax, pico, anual['year'])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    ax.set_ylim(0, anual['pixeles'].max() * 1.3)  # espacio para la anotación del pico
    ax.set_ylabel('Píxeles anómalos')
    ax.set_title('Evolución anual — volumen de anomalías y peso sobre el área del país')
    ax2 = ax.twinx()
    ax2.plot(anual['year'], anual['pct_colombia'], color=COLOR_2A, lw=1.6, ls='--', marker='s', ms=3,
             label='% del área de Colombia (eje derecho)')
    ax2.set_ylabel('% del área total de Colombia', color=COLOR_2A)
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.3f%%'))
    ax2.tick_params(axis='y', labelcolor=COLOR_2A)
    ax2.grid(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc='upper left', frameon=True, fontsize=8.5, framealpha=0.95)

    _plot_anual_tipo(axes[1], anual_tipo, 'Composición anual por tipo de anomalía',
                     'Año central de la trayectoria')
    fig.suptitle('Nacional — análisis anual', y=1.01)
    fig.tight_layout()
    _mostrar(fig, show)

    # 3. Top patrones
    top = df_nac.head(15)
    fig, ax = plt.subplots(figsize=(13, 7.5))
    y = np.arange(len(top))
    ax.barh(y, top['pixeles'], color=[TIPO_COLOR.get(t, '#a0aec0') for t in top['tipo']],
            height=0.7, edgecolor='white')
    ax.set_yticks(y, [_label_tray(t) for t in top['trayectoria']], family='monospace', fontsize=10)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    ax.set_xlabel('Píxeles anómalos (suma de todas las regiones)')
    ax.set_ylabel('Trayectoria (código)')
    ax.set_title('Top 15 trayectorias — total nacional')
    for i, (_, r) in enumerate(top.iterrows()):
        ax.text(r['pixeles'], i, f"  {r['pct_pixeles']:.1f}% · {int(r['n_regiones'])} reg.",
                va='center', fontsize=8.5, color='#4a5568')
    ax.set_xlim(0, top['pixeles'].max() * 1.3)
    _leyenda_tipos(ax, loc='lower right')
    fig.tight_layout()
    fig.subplots_adjust(left=0.16)
    _mostrar(fig, show)

    # 4. Concentración + extensión geográfica
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    x = np.arange(1, len(cum) + 1)
    axes[0].fill_between(x, cum.values, color=COLOR_1A, alpha=0.12)
    axes[0].plot(x, cum.values, color=COLOR_1A, lw=2, label='Fracción acumulada de píxeles')
    axes[0].axhline(0.8, color=COLOR_2A, ls='--', lw=1.1, label='Umbral 80%')
    axes[0].axhline(0.95, color=COLOR_REV, ls=':', lw=1.1, label='Umbral 95%')
    axes[0].axvline(n80, color=COLOR_2A, ls='--', lw=0.9, alpha=0.7)
    axes[0].set_ylim(0, 1.02)
    axes[0].set_xlabel('N.º de patrones acumulados (mayor → menor)')
    axes[0].set_ylabel('Fracción acumulada de píxeles anómalos')
    axes[0].set_title(f'Concentración: {n80} patrones ≈ 80% de píxeles')
    axes[0].legend(loc='lower right', fontsize=8.5, framealpha=0.95)

    for tipo in TIPO_ORDEN:
        g = df_nac[df_nac['tipo'] == tipo]
        if g.empty:
            continue
        axes[1].scatter(
            g['n_regiones'], g['pixeles'],
            s=np.clip(30 + g['pct_pixeles'] * 6, 18, 220),
            c=TIPO_COLOR[tipo], alpha=0.75,
            edgecolors='white', linewidths=0.5, label=f'{TIPO_SHORT[tipo]} — {tipo}',
        )
    for _, r in df_nac.head(6).iterrows():
        axes[1].annotate(r['trayectoria'], (r['n_regiones'], r['pixeles']),
                         textcoords='offset points', xytext=(5, 3),
                         fontsize=8, family='monospace', color='#2d3748')
    axes[1].set_yscale('log')
    axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    axes[1].set_xlabel('N.º de regiones donde aparece el patrón')
    axes[1].set_ylabel('Píxeles anómalos (escala log)')
    axes[1].set_title('Extensión geográfica vs magnitud del patrón')
    axes[1].legend(fontsize=8.5, title='Tipo de anomalía', title_fontsize=9, framealpha=0.95)
    fig.suptitle('Nacional — concentración y extensión', y=1.02)
    fig.tight_layout()
    _mostrar(fig, show)

    print('\nTop 12 trayectorias nacionales')
    _tabla(
        df_nac.head(12),
        {
            'trayectoria': 'Trayectoria',
            'tipo': 'Tipo de anomalía',
            'pixeles': 'Píxeles anómalos',
            'n_regiones': 'Regiones',
            'pct_pixeles': '% de los píxeles anómalos del país',
        },
        {'pixeles': '{:,.0f}', 'pct_pixeles': '{:.2f}%'},
        n=12,
    )
    print('\nAños con mayor volumen de anomalías')
    _tabla(
        anual.sort_values('pixeles', ascending=False),
        {
            'year': 'Año',
            'pixeles': 'Píxeles anómalos',
            'pct_colombia': '% del área de Colombia',
            'n_regiones': 'Regiones afectadas',
            'n_patrones': 'Patrones distintos',
        },
        {'year': '{:.0f}', 'pixeles': '{:,.0f}', 'pct_colombia': '{:.3f}%'},
        n=5,
    )
    return {'patrones': df_nac, 'anual': anual, 'anual_tipo': anual_tipo, 'por_tipo': por_tipo}


def analizar_region(
    region_id: str | int,
    df: pd.DataFrame | None = None,
    total_colombia: int = TOTAL_COLOMBIA_DEFAULT,
    show: bool = True,
):
    """Análisis enfocado en una sola región (REGION_ID definido)."""
    _style()
    rid = str(region_id)
    src = cargar_csv() if df is None else _ensure_trayectoria(df)
    reg = src[src['region_id'] == rid].copy()
    if reg.empty:
        raise ValueError(f'No hay filas para la región {rid} en el CSV.')

    nac_anual = serie_anual(src)
    reg_pat = agregar_patrones(reg)
    nac_pat = agregar_patrones(src)[['trayectoria', 'pixeles', 'n_regiones']].rename(
        columns={'pixeles': 'pixeles_nac', 'n_regiones': 'n_regiones_nac'}
    )
    reg_pat = reg_pat.merge(nac_pat, on='trayectoria', how='left')
    reg_pat['share_nac'] = (100 * reg_pat['pixeles'] / reg_pat['pixeles_nac']).round(2)

    total_reg = int(reg_pat['pixeles'].sum())
    total_nac = int(src['pixeles'].sum())
    share_pais = 100 * total_reg / total_nac
    por_tipo = (
        reg_pat.groupby('tipo', as_index=False)['pixeles']
        .sum()
        .sort_values('pixeles', ascending=False)
    )
    anual = serie_anual(reg)
    anual = anual.merge(
        nac_anual[['year', 'pixeles']].rename(columns={'pixeles': 'pixeles_nac'}),
        on='year', how='left',
    )
    anual['pct_del_nacional'] = 100 * anual['pixeles'] / anual['pixeles_nac']
    anual_tipo = serie_anual_tipo(reg)
    pico = anual.loc[anual['pixeles'].idxmax()]

    print(f'=== Analisis REGIONAL - region {rid} ===')
    print(f'  Pixeles anomalos:    {total_reg:,}')
    print(f'  Peso en el pais:     {share_pais:.2f}% de los {total_nac:,} pixeles anomalos nacionales')
    print('                       (NO es el tamano de la region respecto a Colombia)')
    print(f'  Patrones distintos:  {len(reg_pat):,}')
    print(f'  Patron dominante:    {reg_pat.iloc[0]["trayectoria"]} ({reg_pat.iloc[0]["pct_pixeles"]:.1f}% de la region)')
    print(f'  Anio pico:           {int(pico["year"])} -> {int(pico["pixeles"]):,} px '
          f'({pico["pct_del_nacional"]:.2f}% de los anomalos del pais ese anio)')

    # 1. KPIs regionales + tipo
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8), gridspec_kw={'width_ratios': [1.05, 1.25]})
    _plot_kpis(axes[0], [
        ('Región', rid),
        ('Píxeles anómalos', f'{total_reg:,}'),
        ('% de los píxeles anómalos del país', f'{share_pais:.2f}%'),
        ('Patrones distintos', f'{len(reg_pat):,}'),
        ('Patrón dominante', str(reg_pat.iloc[0]['trayectoria'])),
        ('Año pico', f'{int(pico["year"])}'),
    ], f'Indicadores · región {rid}')
    _plot_tipo_barras(axes[1], por_tipo, total_reg, f'Composición por tipo de anomalía · {rid}')
    fig.suptitle(f'Región {rid} — resumen (peso medido en píxeles anómalos, no en área)', y=1.03)
    fig.tight_layout()
    _mostrar(fig, show)

    # 2. Anual región vs contexto nacional
    fig, axes = plt.subplots(2, 1, figsize=(13, 8.6), sharex=True, gridspec_kw={'height_ratios': [1.15, 1]})
    ax = axes[0]
    ax.fill_between(anual['year'], anual['pixeles'], color=COLOR_REG, alpha=0.18)
    ax.plot(anual['year'], anual['pixeles'], color=COLOR_REG, lw=2.3, marker='o', ms=3.5,
            label=f'Píxeles anómalos en {rid} (eje izquierdo)')
    ax.scatter([pico['year']], [pico['pixeles']], color=COLOR_2A, zorder=3, s=55)
    _anotar_pico(ax, pico, anual['year'])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    ax.set_ylim(0, anual['pixeles'].max() * 1.3)  # espacio para la anotación del pico
    ax.set_ylabel(f'Píxeles anómalos en {rid}')
    ax.set_title(f'Evolución anual · región {rid} y su aporte al total del país')
    ax2 = ax.twinx()
    ax2.plot(anual['year'], anual['pct_del_nacional'], color=COLOR_2A, lw=1.5, ls='--', marker='s', ms=3,
             label='% de los píxeles anómalos del país ese año (eje derecho)')
    ax2.set_ylabel('% de los anómalos del país', color=COLOR_2A)
    ax2.tick_params(axis='y', labelcolor=COLOR_2A)
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f%%'))
    ax2.set_ylim(0, max(anual['pct_del_nacional'].max() * 1.35, 0.5))
    ax2.grid(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc='upper left', fontsize=8.5, framealpha=0.95)

    _plot_anual_tipo(axes[1], anual_tipo, f'Composición anual por tipo · región {rid}', 'Año')
    fig.suptitle(f'Región {rid} — análisis anual', y=1.01)
    fig.tight_layout()
    _mostrar(fig, show)

    # 3. Top patrones de la región + peso en el nacional
    top = reg_pat.head(10)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.8), gridspec_kw={'width_ratios': [1.15, 1]})
    y = np.arange(len(top))
    labels = [_label_tray(t) for t in top['trayectoria']]

    axes[0].barh(y, top['pixeles'], color=[TIPO_COLOR.get(t, '#a0aec0') for t in top['tipo']],
                 height=0.7, edgecolor='white')
    axes[0].set_yticks(y, labels, family='monospace', fontsize=10)
    axes[0].invert_yaxis()
    axes[0].xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    axes[0].set_xlabel('Píxeles anómalos en la región')
    axes[0].set_ylabel('Trayectoria (código)')
    axes[0].set_title(f'Top trayectorias en {rid}')
    for i, (_, r) in enumerate(top.iterrows()):
        axes[0].text(r['pixeles'], i, f"  {r['pct_pixeles']:.1f}%",
                     va='center', fontsize=8.5, color='#4a5568')
    axes[0].set_xlim(0, top['pixeles'].max() * 1.28)

    axes[1].barh(y, top['share_nac'].fillna(0), color=COLOR_PESO, height=0.7, edgecolor='white')
    axes[1].set_yticks(y)
    axes[1].set_yticklabels([])
    axes[1].invert_yaxis()
    axes[1].set_xlabel('% del total nacional de ese patrón')
    axes[1].set_title(f'Peso de {rid} en el patrón nacional')
    for i, (_, r) in enumerate(top.iterrows()):
        axes[1].text(r['share_nac'], i, f"  {r['share_nac']:.1f}%",
                     va='center', fontsize=8.5, color='#4a5568')
    axes[1].set_xlim(0, max(top['share_nac'].max() * 1.35, 5))

    # Leyenda única debajo, sin tapar barras
    handles = [mpatches.Patch(color=TIPO_COLOR[t], label=TIPO_SHORT[t]) for t in TIPO_ORDEN]
    handles.append(mpatches.Patch(color=COLOR_PESO, label=f'Aporte de {rid}'))
    fig.legend(handles=handles, loc='lower center', ncol=4, fontsize=9,
               frameon=True, framealpha=0.95, title='Leyenda', title_fontsize=9,
               bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(f'Región {rid} — patrones locales y su peso nacional', y=1.01)
    fig.tight_layout()
    fig.subplots_adjust(left=0.14, bottom=0.18, wspace=0.18)
    _mostrar(fig, show)

    print(f'\nTop 10 trayectorias · región {rid}')
    _tabla(
        top,
        {
            'trayectoria': 'Trayectoria',
            'tipo': 'Tipo de anomalía',
            'pixeles': 'Píxeles en la región',
            'pct_pixeles': '% de la región',
            'share_nac': '% del total nacional de ese patrón',
            'n_regiones_nac': 'Regiones con ese patrón',
        },
        {'pixeles': '{:,.0f}', 'pct_pixeles': '{:.2f}%', 'share_nac': '{:.2f}%'},
        n=10,
    )
    print(f'\nAños con mayor volumen · región {rid}')
    _tabla(
        anual.sort_values('pixeles', ascending=False),
        {
            'year': 'Año',
            'pixeles': 'Píxeles en la región',
            'pixeles_nac': 'Píxeles anómalos del país',
            'pct_del_nacional': '% de los anómalos del país ese año',
            'n_patrones': 'Patrones distintos',
        },
        {
            'year': '{:.0f}',
            'pixeles': '{:,.0f}',
            'pixeles_nac': '{:,.0f}',
            'pct_del_nacional': '{:.2f}%',
        },
        n=5,
    )
    return {'patrones': reg_pat, 'anual': anual, 'anual_tipo': anual_tipo, 'por_tipo': por_tipo}


def analizar(
    region_id=None,
    df: pd.DataFrame | None = None,
    total_colombia: int = TOTAL_COLOMBIA_DEFAULT,
    show: bool = True,
):
    """Despacha: REGION_ID → análisis regional; None → nacional."""
    if region_id is None or (isinstance(region_id, float) and np.isnan(region_id)):
        return analizar_nacional(df=df, total_colombia=total_colombia, show=show)
    return analizar_region(region_id, df=df, total_colombia=total_colombia, show=show)
