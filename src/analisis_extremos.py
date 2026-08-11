from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

import analisis_nacional as an

from paths import CSV_ANOMALIAS as CSV, TEST_FIGS
COLOR_1 = '#2b6cb0'
COLOR_2 = '#c05621'
COLOR_R = '#718096'


def _fmt_k(x, _pos=None):
    if abs(x) >= 1_000_000:
        return f'{x / 1_000_000:.1f}M'
    if abs(x) >= 1_000:
        return f'{x / 1_000:.0f}k'
    return f'{int(x)}'


def cargar(path: Path | str | None = None) -> pd.DataFrame:
    df = an.cargar_csv(path or CSV)
    if 'year' not in df.columns:
        raise ValueError('El CSV debe incluir la columna year')
    return df


def clasificar_ventana(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    c1, c2, c3, c4 = out['clase_1'], out['clase_2'], out['clase_3'], out['clase_4']
    out['es_1_anio'] = (c2 == 3) & (c3 != 3)
    out['es_2_anios'] = (c2 == 3) & (c3 == 3) & (c4 != 3)
    out['es_parpadeo'] = (c2 == 3) & (c3 != 3) & (c4 == 3)
    out['anio_corte_2'] = np.where(out['es_2_anios'], out['year'] + 2, np.nan)
    out['anio_corte_1'] = np.where(out['es_1_anio'], out['year'] + 1, np.nan)
    return out


def resumen_2023(df: pd.DataFrame) -> pd.DataFrame:
    s = clasificar_ventana(df[df['year'] == 2023])
    total = s['pixeles'].sum()
    m2 = s['es_2_anios']
    m_parp = s['es_parpadeo']
    m1 = s['es_1_anio'] & ~m_parp
    filas = [
        ('Bosque 1 año (corta en 2024)', m1, '2022 → 2023=3 → 2024≠3 → 2025≠3'),
        ('Bosque 2 años (corta en 2025)', m2, '2022 → 2023=3 → 2024=3 → 2025≠3'),
        ('Parpadeo (bosque–no bosque–bosque)', m_parp, 'Ejemplo: 21-3-21-3'),
    ]
    rows = []
    for nombre, mask, nota in filas:
        px = int(s.loc[mask, 'pixeles'].sum())
        rows.append({
            'caso': nombre,
            'pixeles': px,
            'pct_de_2023': round(100 * px / total, 1) if total else 0.0,
            'ventana': nota,
        })
    return pd.DataFrame(rows)


def serie_por_tipo_estructural(df: pd.DataFrame) -> pd.DataFrame:
    s = clasificar_ventana(df)
    rows = []
    for y in sorted(s['year'].unique()):
        sy = s[s['year'] == y]
        rows.append({
            'year': y,
            'px_1_anio': int(sy.loc[sy['es_1_anio'], 'pixeles'].sum()),
            'px_2_anios': int(sy.loc[sy['es_2_anios'], 'pixeles'].sum()),
            'px_parpadeo': int(sy.loc[sy['es_parpadeo'], 'pixeles'].sum()),
            'px_total': int(sy['pixeles'].sum()),
        })
    return pd.DataFrame(rows)


def cortes_bloques_2_anios(df: pd.DataFrame) -> pd.DataFrame:
    s = clasificar_ventana(df)
    s2 = s[s['es_2_anios']].copy()
    s2['anio_corte'] = s2['year'] + 2
    return (
        s2.groupby('anio_corte', as_index=False)['pixeles']
        .sum()
        .rename(columns={'pixeles': 'px_corte'})
        .sort_values('anio_corte')
    )


def cortes_bloques_1_anio(df: pd.DataFrame) -> pd.DataFrame:
    s = clasificar_ventana(df)
    s1 = s[s['es_1_anio']].copy()
    s1['anio_corte'] = s1['year'] + 1
    return (
        s1.groupby('anio_corte', as_index=False)['pixeles']
        .sum()
        .rename(columns={'pixeles': 'px_corte'})
        .sort_values('anio_corte')
    )


def analizar_extremos(df: pd.DataFrame | None = None, show: bool = True):
    an._style()
    src = cargar() if df is None else clasificar_ventana(an._ensure_trayectoria(df))
    if 'es_1_anio' not in src.columns:
        src = clasificar_ventana(src)

    serie = serie_por_tipo_estructural(src)
    corte2 = cortes_bloques_2_anios(src)
    corte1 = cortes_bloques_1_anio(src)
    r23 = resumen_2023(src)

    print('=== Final de serie (2023–2025) ===')
    print('Anomalías con año central 2023:')
    print(r23.to_string(index=False))

    fig, ax = plt.subplots(figsize=(13, 4.8))
    ax.bar(serie['year'], serie['px_1_anio'], color=COLOR_1, width=0.85, label='1 año (finaliza en t+1)')
    ax.bar(serie['year'], serie['px_2_anios'], bottom=serie['px_1_anio'],
           color=COLOR_2, width=0.85, label='2 años (finaliza en t+2)')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    ax.set_xlabel('Año central (t)')
    ax.set_ylabel('Píxeles anómalos')
    ax.set_title('Bosque aislado según duración')
    ax.legend(loc='upper left', framealpha=0.95)
    if (serie['year'] == 2023).any():
        ax.axvline(2023, color='#c53030', ls='--', lw=1.2, alpha=0.8)
    fig.tight_layout()
    an._mostrar(fig, show)

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    axes[0].bar(corte1['anio_corte'], corte1['px_corte'], color=COLOR_1, width=0.85)
    axes[0].set_title('Finalización de bloques de 1 año (t+1)')
    axes[0].set_xlabel('Año')
    axes[0].set_ylabel('Píxeles')
    axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))

    axes[1].bar(corte2['anio_corte'], corte2['px_corte'], color=COLOR_2, width=0.85)
    axes[1].set_title('Finalización de bloques de 2 años (t+2)')
    axes[1].set_xlabel('Año')
    axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    fig.suptitle('Año en que deja de observarse el bosque del bloque corto', y=1.02)
    fig.tight_layout()
    an._mostrar(fig, show)

    foco = serie[serie['year'].between(2018, 2023)].copy()
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    axes[0].bar(foco['year'], foco['px_total'], color='#a0aec0', width=0.8, label='Total')
    axes[0].bar(foco['year'], foco['px_2_anios'], color=COLOR_2, width=0.55, label='Solo 2 años')
    axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    axes[0].set_title('Anomalías por año central')
    axes[0].set_xlabel('t')
    axes[0].set_ylabel('Píxeles')
    axes[0].legend(framealpha=0.95, fontsize=8.5)

    ends = [2021, 2022, 2023, 2024, 2025]
    px_end_1, px_end_2 = [], []
    for e in ends:
        px_end_1.append(int(corte1.loc[corte1['anio_corte'] == e, 'px_corte'].sum()) if (corte1['anio_corte'] == e).any() else 0)
        px_end_2.append(int(corte2.loc[corte2['anio_corte'] == e, 'px_corte'].sum()) if (corte2['anio_corte'] == e).any() else 0)
    x = np.arange(len(ends))
    axes[1].bar(x - 0.18, px_end_1, width=0.35, color=COLOR_1, label='Corte 1 año')
    axes[1].bar(x + 0.18, px_end_2, width=0.35, color=COLOR_2, label='Corte 2 años')
    axes[1].set_xticks(x, ends)
    axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    axes[1].set_title('Volumen por año de finalización')
    axes[1].set_xlabel('Año')
    axes[1].legend(framealpha=0.95, fontsize=8.5)
    fig.suptitle('Comparación 2018–2025', y=1.02)
    fig.tight_layout()
    an._mostrar(fig, show)

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.5), gridspec_kw={'width_ratios': [1, 1.15]})
    vals = [r23.loc[0, 'pixeles'], r23.loc[1, 'pixeles'], r23.loc[2, 'pixeles']]
    labels = ['1 año\n(finaliza 2024)', '2 años\n(finaliza 2025)', 'Parpadeo']
    axes[0].pie(vals, labels=labels, colors=[COLOR_1, COLOR_2, COLOR_R],
                autopct=lambda p: f'{p:.0f}%', startangle=90,
                textprops={'fontsize': 9, 'color': '#1a202c'})
    axes[0].set_title('Composición · año central 2023')

    axes[1].axis('off')
    axes[1].text(
        0.02, 0.98,
        'Definiciones\n\n'
        '1 año:\n'
        '  t-1 ≠ 3 · t = 3 · t+1 ≠ 3\n'
        '  Ejemplo: 21-3-21-21\n\n'
        '2 años:\n'
        '  t-1 ≠ 3 · t = 3 · t+1 = 3 · t+2 ≠ 3\n'
        '  Ejemplo: 21-3-3-21\n\n'
        'Parpadeo:\n'
        '  t = 3 · t+1 ≠ 3 · t+2 = 3\n'
        '  Ejemplo: 21-3-21-3\n\n'
        'Para t = 2023:\n'
        '  finalización en t+1 → 2024\n'
        '  finalización en t+2 → 2025',
        va='top', ha='left', family='monospace', fontsize=9.2,
        color='#1a202c', transform=axes[1].transAxes,
    )
    fig.tight_layout()
    an._mostrar(fig, show)

    return {
        'serie': serie,
        'corte_1': corte1,
        'corte_2': corte2,
        'resumen_2023': r23,
    }


if __name__ == '__main__':
    analizar_extremos(show=False)
    out = TEST_FIGS
    out.mkdir(exist_ok=True)
    for i, n in enumerate(plt.get_fignums(), 1):
        fig = plt.figure(n)
        fig.savefig(out / f'extremos_{i:02d}.png', dpi=120, bbox_inches='tight', facecolor='white')
    print('Figuras en', out)
