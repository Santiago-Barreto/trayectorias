from __future__ import annotations

from pathlib import Path

import ee
import pandas as pd
import plotly.graph_objects as go
from IPython.display import HTML, display
from plotly.subplots import make_subplots

CLASE_BOSQUE = 3


def _nombre(cid: int, class_names: dict | None) -> str:
    if class_names and int(cid) in class_names:
        nom = str(class_names[int(cid)])
        if '. ' in nom:
            nom = nom.split('. ', 1)[1]
        return nom
    return f'Clase {int(cid)}'


def bandas_clasificacion(imagen, year_min: int = 1985, year_max: int = 2026) -> list[str]:
    disponibles = set(imagen.bandNames().getInfo())
    return [
        f'classification_{y}'
        for y in range(year_min, year_max + 1)
        if f'classification_{y}' in disponibles
    ]


def _ha_clase3_desde_groups(groups) -> float:
    if not groups:
        return 0.0
    total = 0.0
    for item in groups:
        try:
            if int(item.get('class')) == CLASE_BOSQUE:
                total += float(item.get('sum') or 0)
        except (TypeError, ValueError):
            continue
    return total


def detectar_clases(imagen, bands: list[str], geometry, scale: int = 30) -> list[int]:
    paso = max(1, len(bands) // 8)
    muestra = bands[::paso]
    if bands[-1] not in muestra:
        muestra = list(muestra) + [bands[-1]]
    hist = imagen.select(muestra).reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
        tileScale=4,
    ).getInfo() or {}
    clases: set[int] = set()
    for counts in hist.values():
        if not counts:
            continue
        for k in counts:
            try:
                clases.add(int(float(k)))
            except (TypeError, ValueError):
                continue
    return sorted(clases)


def area_clase_por_anio(
    imagen,
    bands: list[str],
    geometry,
    clase: int,
    scale: int = 30,
) -> pd.DataFrame:
    """Una clase × todos los años (1 getInfo). Conservado para tests puntuales."""
    area_bands = []
    for band in bands:
        img_year = imagen.select(band).int16().selfMask()
        ha = (
            ee.Image.pixelArea()
            .divide(1e4)
            .updateMask(img_year.eq(int(clase)))
            .rename(band)
        )
        area_bands.append(ha)

    stats = (
        ee.Image.cat(area_bands)
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True,
            tileScale=4,
        )
        .getInfo()
        or {}
    )
    rows = [
        {'year': int(band.split('_')[-1]), 'clase': int(clase), 'ha': float(stats.get(band, 0) or 0)}
        for band in bands
    ]
    return pd.DataFrame(rows)


def area_bosque_por_anio(imagen, bands, geometry, scale: int = 30) -> pd.DataFrame:
    df = area_clase_por_anio(imagen, bands, geometry, CLASE_BOSQUE, scale=scale)
    return df[['year', 'ha']]


def _groups_a_filas(year: int, groups) -> list[dict]:
    rows = []
    for item in groups or []:
        try:
            cid = int(item.get('class'))
            ha = float(item.get('sum') or 0)
        except (TypeError, ValueError):
            continue
        rows.append({'year': int(year), 'clase': cid, 'ha': ha})
    return rows


def _getinfo_con_reintento(obj, intentos: int = 5, espera: float = 8.0):
    """getInfo con backoff ante 429 (Too many concurrent aggregations)."""
    import time

    ultimo = None
    for i in range(intentos):
        try:
            return obj.getInfo()
        except ee.EEException as err:
            ultimo = err
            msg = str(err).lower()
            if 'too many concurrent' not in msg and '429' not in msg:
                raise
            pause = espera * (1.6 ** i)
            print(f'    GEE 429 → reintento {i + 1}/{intentos} en {pause:.0f}s…', flush=True)
            time.sleep(pause)
    raise ultimo


def areas_todas_clases(
    imagen,
    bands: list[str],
    geometry,
    clases: list[int] | None = None,
    etiqueta: str = '',
    scale: int = 30,
    batch_years: int = 4,
) -> pd.DataFrame:
    """Todas las clases × años, en lotes secuenciales (evita 429 concurrent aggregations).

    Por año: pixelArea/1e4 + group(class). Lotes de `batch_years` (default 4).
    """
    n_lotes = max(1, (len(bands) + batch_years - 1) // batch_years)
    if etiqueta:
        print(
            f'  [{etiqueta}] {n_lotes} consultas GEE · {len(bands)} años '
            f'(lotes de {batch_years})…',
            flush=True,
        )

    rows: list[dict] = []
    for i in range(0, len(bands), batch_years):
        chunk = bands[i:i + batch_years]
        lote = i // batch_years + 1
        if etiqueta:
            print(f'    lote {lote}/{n_lotes}: {[b.split("_")[-1] for b in chunk]}', flush=True)

        feats = []
        for band in chunk:
            year = int(band.split('_')[-1])
            cls = imagen.select(band).rename('class').int16()
            ha = ee.Image.pixelArea().divide(1e4).rename('ha')
            groups = ha.addBands(cls).reduceRegion(
                reducer=ee.Reducer.sum().group(groupField=1, groupName='class'),
                geometry=geometry,
                scale=scale,
                maxPixels=1e13,
                bestEffort=True,
                tileScale=4,
            )
            feats.append(ee.Feature(None, {'year': year, 'groups': groups.get('groups')}))

        info = _getinfo_con_reintento(ee.FeatureCollection(feats)) or {}
        for f in info.get('features') or []:
            props = f.get('properties') or {}
            year = int(props.get('year'))
            rows.extend(_groups_a_filas(year, props.get('groups')))

    if not rows:
        return pd.DataFrame(columns=['year', 'clase', 'ha', 'fuente'])

    out = pd.DataFrame(rows)
    if clases is not None:
        allow = {int(c) for c in clases}
        out = out[out['clase'].isin(allow)]
    if clases is not None and bands:
        years = [int(b.split('_')[-1]) for b in bands]
        grid = pd.MultiIndex.from_product(
            [years, [int(c) for c in clases]], names=['year', 'clase']
        ).to_frame(index=False)
        out = grid.merge(out, on=['year', 'clase'], how='left').fillna({'ha': 0.0})

    out['fuente'] = etiqueta
    return out.reset_index(drop=True)


def calcular(
    img_original,
    img_corregida,
    geometry=None,
    class_names: dict | None = None,
    year_min: int = 1985,
    year_max: int = 2026,
    scale: int = 30,
) -> pd.DataFrame:
    bands = bandas_clasificacion(img_original, year_min, year_max)
    if not bands:
        raise ValueError('No se encontraron bandas classification_YYYY.')

    if geometry is None:
        print('Aviso: sin ROI vectorial → se usa imagen.geometry() (puede diferir del CSV GEE)')
        geom = img_original.geometry()
    else:
        inter = geometry.intersection(img_original.geometry(), 1).area(1).getInfo()
        if not inter or inter <= 0:
            raise ValueError(
                'ROI vectorial sin overlap con el asset. '
                'Revisa REGION_VECTOR (usar clasificacion-regiones-3-buffer-250m).'
            )
        geom = geometry

    print(
        f'Calculando áreas (pixelArea/1e4) · {len(bands)} años · '
        f'lotes secuenciales (original + corregida)…',
        flush=True,
    )
    so = areas_todas_clases(img_original, bands, geom, clases=None, etiqueta='original', scale=scale)
    sc = areas_todas_clases(img_corregida, bands, geom, clases=None, etiqueta='corregida', scale=scale)

    clases = sorted(set(so['clase'].astype(int)).union(set(sc['clase'].astype(int))))
    if not clases:
        raise ValueError('No se detectaron clases en la ROI.')
    print(f'Clases: {clases}')

    # Misma grilla year×clase en ambas fuentes (ceros donde falte)
    years = [int(b.split('_')[-1]) for b in bands]
    grid = pd.MultiIndex.from_product([years, clases], names=['year', 'clase']).to_frame(index=False)
    so = grid.merge(so[['year', 'clase', 'ha']], on=['year', 'clase'], how='left').fillna({'ha': 0.0})
    sc = grid.merge(sc[['year', 'clase', 'ha']], on=['year', 'clase'], how='left').fillna({'ha': 0.0})

    serie = so.rename(columns={'ha': 'ha_original'})[['year', 'clase', 'ha_original']].merge(
        sc.rename(columns={'ha': 'ha_corregida'})[['year', 'clase', 'ha_corregida']],
        on=['year', 'clase'],
        how='outer',
    ).fillna(0.0)
    serie['delta_ha'] = serie['ha_corregida'] - serie['ha_original']
    serie['nombre'] = serie['clase'].map(lambda c: _nombre(int(c), class_names))
    serie = serie.sort_values(['clase', 'year']).reset_index(drop=True)
    return serie


def resumen_por_clase(serie: pd.DataFrame) -> pd.DataFrame:
    g = serie.groupby(['clase', 'nombre'], as_index=False).agg(
        ha_media_original=('ha_original', 'mean'),
        ha_media_corregida=('ha_corregida', 'mean'),
        ha_total_original=('ha_original', 'sum'),
        ha_total_corregida=('ha_corregida', 'sum'),
        delta_neto=('delta_ha', 'sum'),
        delta_abs_max=('delta_ha', lambda s: s.abs().max()),
    )
    g['delta_pct'] = g.apply(
        lambda r: (
            None if r['ha_total_original'] == 0
            else 100 * r['delta_neto'] / r['ha_total_original']
        ),
        axis=1,
    )
    g['delta_abs_neto'] = g['delta_neto'].abs()
    return g.sort_values('delta_abs_neto', ascending=False).reset_index(drop=True)


def _tabla_texto(df: pd.DataFrame, titulo: str, meta: str = '') -> str:
    lineas = [titulo, meta, df.to_string(index=False), '']
    return '\n'.join(x for x in lineas if x is not None)


def _id_col(cid: int) -> str:
    cid = int(cid)
    return f'ID0{cid}' if cid < 10 else f'ID{cid}'


def _fmt_celda(v: float) -> str:
    try:
        return f'{float(v):,.1f}'
    except (TypeError, ValueError):
        return '0.0'


def _fmt_delta(v: float) -> str:
    try:
        return f'{float(v):+,.1f}'
    except (TypeError, ValueError):
        return '+0.0'


def formatear_resumen(resumen: pd.DataFrame, ambito: str) -> pd.DataFrame:
    out = resumen.copy()
    out['clase'] = out['clase'].astype(int)
    out['ha_media_original'] = out['ha_media_original'].map(_fmt_celda)
    out['ha_media_corregida'] = out['ha_media_corregida'].map(_fmt_celda)
    out['delta_neto'] = out['delta_neto'].map(_fmt_delta)
    out['delta_pct'] = out['delta_pct'].apply(
        lambda v: '' if v is None or (isinstance(v, float) and v != v) else f'{float(v):+.2f}%'
    )
    cols = ['clase', 'nombre', 'ha_media_original', 'ha_media_corregida', 'delta_neto', 'delta_pct']
    return out[cols]


def html_resumen(resumen: pd.DataFrame, ambito: str) -> str:
    df = formatear_resumen(resumen, ambito)
    return _tabla_texto(
        df,
        f'Coberturas · {ambito}',
        'ha media anual · delta_neto = suma (corregida - original) · pixelArea/1e4',
    )


def html_tabla_anual(serie: pd.DataFrame, ambito: str) -> str:
    clases = sorted(serie['clase'].unique())
    bloques = []
    for cid in clases:
        col = _id_col(int(cid))
        nombre = serie.loc[serie['clase'] == cid, 'nombre'].iloc[0]
        sub = serie[serie['clase'] == cid].sort_values('year')
        ha_o = sub['ha_original'].astype(float)
        ha_c = sub['ha_corregida'].astype(float)
        delta = ha_c - ha_o
        tabla = pd.DataFrame({
            'year': sub['year'].astype(int).astype(str),
            'original': ha_o.map(_fmt_celda),
            'corregida': ha_c.map(_fmt_celda),
            'delta': delta.map(_fmt_delta),
        })
        total = pd.DataFrame([{
            'year': 'total',
            'original': _fmt_celda(ha_o.sum()),
            'corregida': _fmt_celda(ha_c.sum()),
            'delta': _fmt_delta(delta.sum()),
        }])
        tabla = pd.concat([tabla, total], ignore_index=True)
        titulo = f'{col} · {nombre} · {ambito}'
        meta = 'original vs corregida · ha = pixelArea/1e4'
        bloques.append(_tabla_texto(tabla, titulo, meta))
    return '\n'.join(bloques)


def fig_plotly_coberturas(serie: pd.DataFrame, ambito: str):
    resumen = resumen_por_clase(serie)
    clases = resumen['clase'].tolist()
    labels = {
        int(r['clase']): f"{int(r['clase'])} · {r['nombre']}"
        for _, r in resumen.iterrows()
    }

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.62, 0.38],
        subplot_titles=(
            f'Serie anual por cobertura · {ambito}',
            'Δ neto (suma de años: corregida − original)',
        ),
        vertical_spacing=0.12,
    )

    for i, cid in enumerate(clases):
        sub = serie[serie['clase'] == cid].sort_values('year')
        visible = i == 0
        fig.add_trace(
            go.Scatter(
                x=sub['year'], y=sub['ha_original'],
                name='Original', mode='lines',
                line=dict(color='#2b6cb0', width=2),
                visible=visible,
                showlegend=visible,
                hovertemplate='%{x}: %{y:,.1f} ha<extra>Original</extra>',
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=sub['year'], y=sub['ha_corregida'],
                name='Corregida', mode='lines',
                line=dict(color='#c05621', width=2),
                visible=visible,
                showlegend=visible,
                hovertemplate='%{x}: %{y:,.1f} ha<extra>Corregida</extra>',
            ),
            row=1, col=1,
        )

    n_serie = 2 * len(clases)

    colors = ['#2f855a' if v >= 0 else '#c05621' for v in resumen['delta_neto']]
    fig.add_trace(
        go.Bar(
            x=[labels[int(c)] for c in resumen['clase']],
            y=resumen['delta_neto'],
            marker_color=colors,
            name='Δ neto',
            showlegend=False,
            hovertemplate='%{x}<br>%{y:,.1f} ha<extra></extra>',
        ),
        row=2, col=1,
    )

    buttons = []
    for i, cid in enumerate(clases):
        vis = [False] * n_serie + [True]
        vis[2 * i] = True
        vis[2 * i + 1] = True
        showleg = [False] * n_serie + [False]
        showleg[2 * i] = True
        showleg[2 * i + 1] = True
        buttons.append(dict(
            label=labels[int(cid)],
            method='update',
            args=[
                {'visible': vis, 'showlegend': showleg},
                {'title': f'Coberturas · {ambito} · {labels[int(cid)]}'},
            ],
        ))

    fig.update_layout(
        title=f'Coberturas · {ambito} · {labels[int(clases[0])]}',
        height=720,
        template='plotly_white',
        margin=dict(l=60, r=30, t=80, b=40),
        updatemenus=[dict(
            buttons=buttons,
            direction='down',
            showactive=True,
            x=1.0, xanchor='right',
            y=1.12, yanchor='top',
            bgcolor='#edf2f7',
        )],
        legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
    )
    fig.update_yaxes(title_text='ha', row=1, col=1)
    fig.update_yaxes(title_text='Δ neto (ha)', row=2, col=1)
    fig.update_xaxes(title_text='Año', row=1, col=1)
    return fig


def _mostrar_plotly(fig) -> None:
    import plotly.io as pio
    from IPython.display import display as ipy_display

    pio.renderers.default = 'vscode'
    try:
        ipy_display(fig)
        return
    except Exception as err:
        print(f'Aviso display(fig): {err}')
    try:
        fig.show(renderer='vscode')
        return
    except Exception as err:
        print(f'Aviso fig.show: {err}')
    display(HTML(fig.to_html(include_plotlyjs=True, full_html=False)))


COLS_CSV = [
    'region_id', 'year', 'clase', 'nombre',
    'ha_original', 'ha_corregida', 'delta_ha',
]


def serie_desde_csv(csv_path, region_id) -> pd.DataFrame | None:
    """Carga serie de una región desde CSV; None si no hay filas."""
    path = Path(csv_path)
    if not path.exists():
        return None
    df = pd.read_csv(path, encoding='utf-8-sig')
    if df.empty or 'region_id' not in df.columns:
        return None
    rid = str(region_id).strip()
    sub = df[df['region_id'].astype(str) == rid].copy()
    if sub.empty:
        return None
    need = ['year', 'clase', 'ha_original', 'ha_corregida', 'delta_ha']
    for c in need:
        if c not in sub.columns:
            return None
    if 'nombre' not in sub.columns:
        sub['nombre'] = sub['clase'].map(lambda c: f'Clase {int(c)}')
    return sub[['year', 'clase', 'nombre', 'ha_original', 'ha_corregida', 'delta_ha']].reset_index(drop=True)


def guardar_serie_csv(serie: pd.DataFrame, csv_path, region_id) -> Path:
    """Upsert de la región en el CSV maestro de coberturas."""
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rid = str(region_id).strip()
    block = serie.copy()
    block['region_id'] = rid
    block = block[COLS_CSV]

    if path.exists():
        old = pd.read_csv(path, encoding='utf-8-sig')
        if not old.empty and 'region_id' in old.columns:
            old = old[old['region_id'].astype(str) != rid]
            out = pd.concat([old, block], ignore_index=True)
        else:
            out = block
    else:
        out = block

    out = out.sort_values(['region_id', 'clase', 'year']).reset_index(drop=True)
    out.to_csv(path, index=False, encoding='utf-8-sig')
    return path


def _mostrar_serie(serie: pd.DataFrame, ambito: str):
    resumen = resumen_por_clase(serie)
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.width', 140)
    pd.set_option('display.max_colwidth', 40)
    print(html_resumen(resumen, ambito))
    print(html_tabla_anual(serie, ambito))
    fig = fig_plotly_coberturas(serie, ambito)
    _mostrar_plotly(fig)
    serie.attrs['resumen'] = resumen
    return serie, fig


def calcular_y_mostrar(
    img_original,
    img_corregida,
    region_id=None,
    geometry=None,
    class_names: dict | None = None,
    year_min: int = 1985,
    year_max: int = 2026,
    scale: int = 30,
    csv_path=None,
    forzar_recalculo: bool = False,
):
    """Calcula o lee coberturas desde CSV (caché por región).

    Si `csv_path` existe y la región ya está y `forzar_recalculo=False`,
    no llama a GEE. Tras calcular, hace upsert en el CSV.
    """
    from paths import CSV_COBERTURAS

    if region_id is None:
        print('Estadisticas omitidas: define REGION_ID.')
        return pd.DataFrame(), None

    if csv_path is None:
        csv_path = CSV_COBERTURAS

    ambito = f'Region {region_id}'

    if not forzar_recalculo:
        cached = serie_desde_csv(csv_path, region_id)
        if cached is not None and float(cached['ha_original'].sum()) > 0:
            print(f'Coberturas desde CSV (sin GEE): {Path(csv_path).resolve()}')
            print(f'  región {region_id} · {len(cached):,} filas')
            return _mostrar_serie(cached, ambito)

    if img_original is None or img_corregida is None:
        print('Ejecuta primero la celda de carga de datos (seccion 4).')
        return pd.DataFrame(), None

    serie = calcular(
        img_original, img_corregida,
        geometry=geometry,
        class_names=class_names,
        year_min=year_min, year_max=year_max,
        scale=scale,
    )

    if serie.empty or float(serie['ha_original'].sum()) == 0:
        print('Resultado en 0 ha: revisa ROI/asset.')
        return serie, None

    out = guardar_serie_csv(serie, csv_path, region_id)
    print(f'CSV coberturas actualizado: {out.resolve()} · región {region_id}')
    return _mostrar_serie(serie, ambito)
