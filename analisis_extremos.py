"""Análisis visual del final de la serie (2023–2025): 1 año vs 2 años.

Hipótesis: si el problema fuera 2024, el año 2022 (cuya ventana usa 2024 como t+2)
también estaría alto. El pico en 2023 + corte fuerte en 2025 apunta más a 2025
como año de cierre inestable — sin afirmar que eso sea 'malo'.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

import analisis_nacional as an

CSV = Path('trayectorias_imposibles_por_region.csv')
COLOR_1 = '#2b6cb0'
COLOR_2 = '#c05621'
COLOR_R = '#718096'
COLOR_HINT = '#9f7aea'


def _fmt_k(x, _pos=None):
    if abs(x) >= 1_000_000:
        return f'{x / 1_000_000:.1f}M'
    if abs(x) >= 1_000:
        return f'{x / 1_000:.0f}k'
    return f'{int(x)}'


def cargar(path: Path | str | None = None) -> pd.DataFrame:
    df = an.cargar_csv(path or CSV)
    if 'year' not in df.columns:
        raise ValueError('El CSV debe tener columna year')
    return df


def clasificar_ventana(df: pd.DataFrame) -> pd.DataFrame:
    """Clasifica cada fila según la ventana t-1…t+2 (no solo la etiqueta tipo)."""
    out = df.copy()
    c1, c2, c3, c4 = out['clase_1'], out['clase_2'], out['clase_3'], out['clase_4']
    # 1 año: bosque solo en t; t+1 ya no es bosque  → entre (t-1) y (t+1)
    out['es_1_anio'] = (c2 == 3) & (c3 != 3)
    # 2 años: bosque en t y t+1; t+2 ya no → entre (t-1) y (t+2)
    out['es_2_anios'] = (c2 == 3) & (c3 == 3) & (c4 != 3)
    # parpadeo / revisar estructural: t bosque, t+1 no, t+2 otra vez bosque
    out['es_parpadeo'] = (c2 == 3) & (c3 != 3) & (c4 == 3)
    out['anio_corte_2'] = np.where(out['es_2_anios'], out['year'] + 2, np.nan)
    out['anio_corte_1'] = np.where(out['es_1_anio'], out['year'] + 1, np.nan)
    return out


def resumen_2023(df: pd.DataFrame) -> pd.DataFrame:
    s = clasificar_ventana(df[df['year'] == 2023])
    total = s['pixeles'].sum()
    # Categorías excluyentes para el gráfico
    m2 = s['es_2_anios']
    m_parp = s['es_parpadeo']
    m1 = s['es_1_anio'] & ~m_parp
    filas = [
        ('1 año limpio (corta en 2024; 2025 no vuelve a 3)', m1,
         '2022 → 2023=3 → 2024≠3 → 2025≠3'),
        ('2 años (bosque 2023-2024; corta en 2025)', m2,
         '2022 → 2023=3 → 2024=3 → 2025≠3'),
        ('Parpadeo (3 en 2023, no en 2024, otra vez 3 en 2025)', m_parp,
         'p. ej. 21-3-21-3'),
    ]
    rows = []
    for nombre, mask, nota in filas:
        px = int(s.loc[mask, 'pixeles'].sum())
        rows.append({
            'caso': nombre,
            'pixeles': px,
            'pct_de_2023': round(100 * px / total, 1) if total else 0.0,
            'lectura': nota,
        })
    return pd.DataFrame(rows)


def serie_por_tipo_estructural(df: pd.DataFrame) -> pd.DataFrame:
    s = clasificar_ventana(df)
    years = sorted(s['year'].unique())
    rows = []
    for y in years:
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
    """Suma de píxeles de bloques 2 años según el año en que cortan (t+2)."""
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
    """Genera figuras para interpretar el pico 2023 y el rol de 2024/2025."""
    an._style()
    src = cargar() if df is None else clasificar_ventana(an._ensure_trayectoria(df))
    if 'es_1_anio' not in src.columns:
        src = clasificar_ventana(src)

    serie = serie_por_tipo_estructural(src)
    corte2 = cortes_bloques_2_anios(src)
    corte1 = cortes_bloques_1_anio(src)
    r23 = resumen_2023(src)

    print('=== Extremos de serie (foco 2023-2025) ===')
    print('Importante: un pico no prueba por sí solo que un año esté "mal".')
    print('Solo indica muchas ventanas cortas de bosque ancladas ahí.\n')
    print('Desglose de anomalías con año central 2023:')
    display_df = r23.copy()
    print(display_df.to_string(index=False))

    # --- Fig 1: serie apilada 1 vs 2 años ---
    fig, ax = plt.subplots(figsize=(13, 4.8))
    ax.bar(serie['year'], serie['px_1_anio'], color=COLOR_1, width=0.85, label='1 año (corta en t+1)')
    ax.bar(serie['year'], serie['px_2_anios'], bottom=serie['px_1_anio'],
           color=COLOR_2, width=0.85, label='2 años (corta en t+2)')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    ax.set_xlabel('Año central de la anomalía (t)')
    ax.set_ylabel('Píxeles anómalos')
    ax.set_title('Anomalías de bosque: ¿1 año o 2 años?')
    ax.legend(loc='upper left', framealpha=0.95)
    ax.axvline(2023, color='#c53030', ls='--', lw=1.2, alpha=0.8)
    ax.annotate('2023', (2023, serie.loc[serie['year'] == 2023, 'px_total'].values[0]),
                textcoords='offset points', xytext=(8, 8), color='#c53030', fontsize=9)
    fig.tight_layout()
    an._mostrar(fig, show)

    # --- Fig 2: dónde cortan los bloques ---
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=False)

    axes[0].bar(corte1['anio_corte'], corte1['px_corte'], color=COLOR_1, width=0.85)
    axes[0].set_title('Bosque de 1 año: año en que ya no es bosque (t+1)')
    axes[0].set_xlabel('Año de corte (t+1)')
    axes[0].set_ylabel('Píxeles')
    axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    for y in (2024, 2025):
        axes[0].axvline(y, color='#c53030', ls=':', lw=1.1, alpha=0.7)

    axes[1].bar(corte2['anio_corte'], corte2['px_corte'], color=COLOR_2, width=0.85)
    axes[1].set_title('Bosque de 2 años: año en que se corta (t+2)')
    axes[1].set_xlabel('Año de corte (t+2)')
    axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    for y in (2024, 2025):
        axes[1].axvline(y, color='#c53030', ls=':', lw=1.1, alpha=0.7)
    # resaltar 2025
    if (corte2['anio_corte'] == 2025).any():
        v = corte2.loc[corte2['anio_corte'] == 2025, 'px_corte'].iloc[0]
        axes[1].annotate(f'2025\n{_fmt_k(v)}', (2025, v), textcoords='offset points',
                         xytext=(0, 10), ha='center', color='#c53030', fontsize=9)

    fig.suptitle('¿Dónde se “rompe” el bosque corto? (2024 vs 2025)', y=1.02)
    fig.tight_layout()
    an._mostrar(fig, show)

    # --- Fig 3: test de la hipótesis 2024 vs 2025 ---
    # Si 2024 fuera el problema del corte a 2 años, year=2022 debería estar alto.
    foco = serie[serie['year'].between(2018, 2023)].copy()
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))

    axes[0].bar(foco['year'], foco['px_total'], color='#a0aec0', width=0.8, label='Total anómalos')
    axes[0].bar(foco['year'], foco['px_2_anios'], color=COLOR_2, width=0.55, label='Solo 2 años')
    axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    axes[0].set_title('Año central t (anomalía)')
    axes[0].set_xlabel('t')
    axes[0].set_ylabel('Píxeles')
    axes[0].legend(framealpha=0.95, fontsize=8.5)
    axes[0].annotate('Si 2024 fuera el corte\nproblemático, 2022\ntambién estaría alto',
                     xy=(2022, foco.loc[foco['year'] == 2022, 'px_2_anios'].values[0]),
                     xytext=(2018.2, foco['px_total'].max() * 0.72),
                     fontsize=8.5, color='#4a5568',
                     arrowprops=dict(arrowstyle='->', color='#718096'))

    # barras explícitas: volumen que CORTA en 2023, 2024, 2025
    ends = [2021, 2022, 2023, 2024, 2025]
    px_end_1 = []
    px_end_2 = []
    for e in ends:
        px_end_1.append(int(corte1.loc[corte1['anio_corte'] == e, 'px_corte'].sum()) if (corte1['anio_corte'] == e).any() else 0)
        px_end_2.append(int(corte2.loc[corte2['anio_corte'] == e, 'px_corte'].sum()) if (corte2['anio_corte'] == e).any() else 0)

    x = np.arange(len(ends))
    axes[1].bar(x - 0.18, px_end_1, width=0.35, color=COLOR_1, label='Corte de 1 año (t+1)')
    axes[1].bar(x + 0.18, px_end_2, width=0.35, color=COLOR_2, label='Corte de 2 años (t+2)')
    axes[1].set_xticks(x, ends)
    axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))
    axes[1].set_title('Volumen según año de corte')
    axes[1].set_xlabel('Año donde deja de ser bosque')
    axes[1].legend(framealpha=0.95, fontsize=8.5)
    axes[1].annotate('2025 destaca\nen cortes a 2 años',
                     xy=(list(ends).index(2025) + 0.18, px_end_2[ends.index(2025)]),
                     xytext=(0.5, max(px_end_2) * 0.75),
                     fontsize=8.5, color='#c53030',
                     arrowprops=dict(arrowstyle='->', color='#c53030'))

    fig.suptitle('Prueba rápida: ¿problema más de 2024 o de 2025?', y=1.02)
    fig.tight_layout()
    an._mostrar(fig, show)

    # --- Fig 4: zoom 2023 composición + ejemplos ---
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.5), gridspec_kw={'width_ratios': [1, 1.15]})
    vals = [r23.loc[0, 'pixeles'], r23.loc[1, 'pixeles'], r23.loc[2, 'pixeles']]
    labels = ['1 año\n(corta 2024)', '2 años\n(corta 2025)', 'Parpadeo']
    colors = [COLOR_1, COLOR_2, COLOR_R]
    axes[0].pie(vals, labels=labels, colors=colors, autopct=lambda p: f'{p:.0f}%',
                startangle=90, textprops={'fontsize': 9, 'color': '#1a202c'})
    axes[0].set_title('Composición de anomalías con t = 2023')

    axes[1].axis('off')
    texto = (
        "Cómo leer 2023\n\n"
        "1 año limpio (entre 2022 y 2024):\n"
        "  2022 ≠ 3 · 2023 = 3 · 2024 ≠ 3 · 2025 ≠ 3\n"
        "  Ej.: 21-3-21-21\n\n"
        "2 años (entre 2022 y 2025):\n"
        "  2022 ≠ 3 · 2023 = 3 · 2024 = 3 · 2025 ≠ 3\n"
        "  Ej.: 21-3-3-21  ← suele dominar el pico\n\n"
        "Parpadeo:\n"
        "  2023 = 3 · 2024 ≠ 3 · 2025 = 3\n\n"
        "Si el corte problemático fuera 2024,\n"
        "los bloques de 2 años con t=2022\n"
        "(que cortan en 2024) estarían altos.\n"
        "Como 2022 no se dispara igual que 2023,\n"
        "la señal apunta más al cierre en 2025.\n\n"
        "Ojo: eso describe inestabilidad de la\n"
        "ventana, no un veredicto de calidad."
    )
    axes[1].text(0.02, 0.98, texto, va='top', ha='left', family='monospace',
                 fontsize=9.2, color='#1a202c', transform=axes[1].transAxes)
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
    out = Path('_test_figs')
    out.mkdir(exist_ok=True)
    for i, n in enumerate(plt.get_fignums(), 1):
        fig = plt.figure(n)
        fig.savefig(out / f'extremos_{i:02d}.png', dpi=120, bbox_inches='tight', facecolor='white')
    print('Figuras en', out)
