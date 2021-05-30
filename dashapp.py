from datetime import timedelta
import os
import dash
from dash.exceptions import PreventUpdate
import dash_deck
import dash_table
import psycopg2
from numpy import result_type
import pydeck
import pytz
import dash_bootstrap_components as dbc
from dateutil.parser import parse
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine

from utils.perf import PerfCounter
from calc.trips import (
    filter_trips, read_locations, read_uuids, split_trip_legs, get_transit_locations, LOCAL_2D_CRS
)


import os; import django; os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mocaf.settings"); django.setup()  # noqa
from trips.models import Device


from dotenv import load_dotenv
load_dotenv()

DEFAULT_ZOOM = 12
DEFAULT_UUID = os.getenv('DEFAULT_UUID')

LOCAL_TZ = pytz.timezone('Europe/Helsinki')

eng = create_engine(os.getenv('DATABASE_URL'))


COLOR_MAP = {
    'still': '#073b4c',
    'walking': '#ffd166',
    'on_foot': '#ffd166',
    'in_vehicle': '#ef476f',
    'running': '#f77f00',
    'on_bicycle': '#06d6a0',
    'unknown': '#cccccc',
    'tram': '#251b5f',
    'bus': '#354bb7',
    'car': '#ef476f',
    'train': '#7db93e',
    'other': '#aaaaaa',
}

TRANSPORT_COLOR_MAP = {
    'bicycle': COLOR_MAP['on_bicycle'],
    'car': COLOR_MAP['in_vehicle'],
    'walk': COLOR_MAP['walking'],
}


def hex_to_rgba(value):
    value = value.lstrip('#')
    lv = len(value)
    colors = list(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
    return colors


COLOR_MAP_RGB = {atype: hex_to_rgba(color) for atype, color in COLOR_MAP.items()}


locations_df = None
locations_uuid = None
time_filtered_locations_df = None
map_component = None
trip_component = None
data_table_component = None
filters_enabled = False


def engine_connect() -> psycopg2.extensions.connection:
    conn = eng.connect().connection
    return conn


conn = engine_connect()

uuids = read_uuids(conn)
device_by_uuid = {str(dev.uuid): dev for dev in Device.objects.filter(uuid__in=uuids)}
if DEFAULT_UUID and DEFAULT_UUID not in uuids:
    uuids.insert(0, DEFAULT_UUID)


map_view = pydeck.View("MapView", width="100%", height="100%", controller=True)


def make_transit_layer(df):
    if df.time.max() - df.time.min() > timedelta(hours=1):
        return None

    print('reading transit')
    trdf = get_transit_locations(conn, locations_uuid, df.time.min(), df.time.max())
    print('transit rows:')
    print(trdf)
    if not len(trdf):
        return None

    trdf = gpd.GeoDataFrame(trdf, geometry=gpd.points_from_xy(trdf.x, trdf.y, crs=LOCAL_2D_CRS))
    trdf['geometry'] = trdf['geometry'].to_crs(4326)
    trdf['lon'] = trdf.geometry.x
    trdf['lat'] = trdf.geometry.y
    trdf['local_time'] = pd.to_datetime(trdf.time).dt.tz_convert(LOCAL_TZ).dt.round('1s')
    trdf['time_str'] = trdf.local_time.astype(str)
    trdf['description'] = trdf.vehicle_journey_ref

    tr_layer = pydeck.Layer(
        'PointCloudLayer',
        trdf,
        get_position=['lon', 'lat'],
        auto_highlight=True,
        get_color=[180, 0, 200, 140],
        pickable=True,
        point_size=12,
    )
    return tr_layer


def make_map_component(xstart=None, xend=None):
    PerfCounter('make_map_fig')

    df = time_filtered_locations_df.copy()

    df['opacity'] = (df.time - df.time.min()) / (df.time.max() - df.time.min())
    df['opacity'] = (150 + df.opacity * 100).astype(int)
    df.loc[df.trip_id == -1, 'opacity'] = 50
    df['color'] = df[['atype', 'opacity']].apply(
        lambda x: [*COLOR_MAP_RGB[x.atype], x.opacity],
        axis=1, result_type='reduce',
    )
    df.loc_error = df.loc_error.fillna(value=-1)
    df.aconf = df.aconf.fillna(value=-1)
    df['time_str'] = df.local_time.astype(str)
    df.speed = (df.speed * 3.6).fillna(value=-1)
    df = df[[
        'lon', 'lat', 'loc_error', 'color', 'aconf', 'speed', 'time_str', 'atype',
        'battery_charging', 'atypef', 'closest_car_way_name', 'closest_car_way_dist',
    ]]
    df.atypef = df.atypef.fillna(value='')
    df.closest_car_way_name = df.closest_car_way_name.fillna(value='')
    df.closest_car_way_dist = df.closest_car_way_dist.round(1).fillna(value=-1)
    df.battery_charging = df.battery_charging.fillna(value=False)
    df['description'] = df[['atype', 'atypef']].apply(
        lambda x: '%s -> %s' % (x.atype, x.atypef),
        axis=1
        )
    df = df.dropna()
    layer = pydeck.Layer(
        'PointCloudLayer',
        df,
        get_position=['lon', 'lat'], # , 'speed'
        # get_position=['lon', 'lat'],
        auto_highlight=True,
        get_radius='loc_error < 20 ? loc_error * 1.5 : 20 * 1.5',
        get_color='color',
        pickable=True,
        point_size=8,
    )

    all_layers = [layer]

    tr_layer = make_transit_layer(time_filtered_locations_df)
    if tr_layer is not None:
        all_layers.append(tr_layer)

    initial_view_state = pydeck.data_utils.viewport_helpers.compute_view(df[['lon', 'lat']])
    if initial_view_state.zoom > 15:
        initial_view_state.zoom = 15

    TOOLTIP_TEXT = {
        'html': '{time_str}<br />{description}<br />Speed: {speed} km/h<br />' +
            'Loc. error: {loc_error} m<br />' +
            'Battery charging: {battery_charging}<br />'
            'Closest car way: {closest_car_way_name}<br />'
            'Closest car way distance: {closest_car_way_dist} m'
    }

    r = pydeck.Deck(
        layers=all_layers,
        initial_view_state=initial_view_state,
        # map_provider='mapbox',
        map_style='mapbox://styles/mapbox/streets-v11',
    )

    dc = dash_deck.DeckGL(
        data=r.to_json(), id="deck-gl", mapboxKey=os.getenv('MAPBOX_ACCESS_TOKEN'),
        tooltip=TOOLTIP_TEXT
    )

    return dc


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i: i + 2], 16) for i in (0, 2, 4))


def make_trip_component():
    device = Device.objects.filter(uuid=locations_uuid).first()
    if not device:
        return None

    pc = PerfCounter('make trip_component')
    pc.display('fetching trips')
    df = time_filtered_locations_df
    start = df['local_time'].min()
    end = df['local_time'].max()

    trips = device.trips.all()
    trips = trips.started_during(start, end).prefetch_related('legs', 'legs__locations')
    pc.display('fetched %d trips' % len(trips))

    recs = []
    for trip in trips:
        legs = list(trip.legs.all())
        for idx, leg in enumerate(legs):
            path = [[p.loc.x, p.loc.y] for p in leg.locations.all()]
            name = 'Trip %d, leg %d/%d: %s' % (trip.id, idx + 1, len(legs), leg.mode.name)
            if leg.user_corrected_mode and leg.estimated_mode:
                name += ' [%s -> %s]' % (leg.estimated_mode.name, leg.user_corrected_mode.name)
            color = hex_to_rgb(TRANSPORT_COLOR_MAP.get(leg.mode.identifier, '#aaaaaa'))
            recs.append(dict(
                name=name, color=color, path=path,
                start_time=leg.start_time.astimezone(LOCAL_TZ).isoformat(),
                end_time=leg.end_time.astimezone(LOCAL_TZ).isoformat(),
            ))

    pc.display('%d legs created' % len(recs))

    initial_view_state = pydeck.data_utils.viewport_helpers.compute_view(df[['lon', 'lat']])
    if initial_view_state.zoom > 15:
        initial_view_state.zoom = 15

    paths_df = pd.DataFrame.from_records(recs)

    layer = pydeck.Layer(
        type='PathLayer',
        data=paths_df,
        pickable=True,
        get_color='color',
        # width_scale=20,
        width_min_pixels=8,
        get_path='path',
        get_width=4,
        auto_highlight=True,
    )

    TOOLTIP_TEXT = {
        'html': '{name}<br />Start: {start_time}<br />End: {end_time}'
    }

    r = pydeck.Deck(
        layers=[layer],
        initial_view_state=initial_view_state,
        map_style='mapbox://styles/mapbox/satellite-streets-v11',
    )
    dc = dash_deck.DeckGL(
        data=r.to_json(), id="deck-gl-trips", mapboxKey=os.getenv('MAPBOX_ACCESS_TOKEN'),
        tooltip=TOOLTIP_TEXT, enableEvents=['click'],
    )

    pc.display('deckgl created')

    return dc


def make_data_table():
    if len(time_filtered_locations_df) > 200:
        return None
    df = time_filtered_locations_df.copy()
    cols = list(df.columns)
    cols.remove('time')
    cols.remove('local_time')
    cols.remove('lon')
    cols.remove('lat')
    df['local_time'] = df.local_time.dt.tz_localize(None).dt.round('1s')
    cols.insert(0, 'local_time')
    table = dash_table.DataTable(
        columns=[{'name': col, 'id': col} for col in cols],
        data=df.to_dict('records'),
        page_action='none',
        style_table={'height': '450px', 'overflowY': 'auto', 'overflowX': 'auto'}
    )
    return table


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
px.set_mapbox_access_token(os.getenv('MAPBOX_ACCESS_TOKEN'))
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

@app.callback(
    [
        Output('map-container', 'children'), Output('trip-container', 'children'),
        Output('data-table-container', 'children')
    ],
    [Input('time-graph', 'clickData'), Input('time-graph', 'relayoutData')])
def display_hover_data(click_data, relayout_data):
    global map_component
    global trip_component
    global data_table_component
    global time_filtered_locations_df

    if not relayout_data or 'xaxis.range[0]' not in relayout_data:
        print('no relayout changes')
        return map_component, trip_component, data_table_component

    print('relayout changed')

    start = relayout_data['xaxis.range[0]']
    end = relayout_data['xaxis.range[1]']

    df = locations_df.copy()
    df = df[(df.local_time >= start) & (df.local_time <= end)]
    time_filtered_locations_df = df

    map_component = make_map_component()
    trip_component = make_trip_component()
    data_table_component = make_data_table()
    return map_component, trip_component, data_table_component

    # if not hover_data and not click_data:
    #     return map_fig
    #
    # if click_data:
    #     click = True
    # else:
    #     click = False
    #
    # layers = []
    # df = locations_df
    # for p in hover_data['points']:
    #     trace = map_fig['data'][p['curveNumber']]
    #     r = df.loc[df.time == p['x']].iloc[0]
    #     layer = dict(
    #         sourcetype='geojson',
    #         source={
    #             'type': 'Feature',
    #             "properties": {},
    #             "geometry": {
    #                 "type": "Point",
    #                 "coordinates": [float(r.lon), float(r.lat)]
    #             },
    #         },
    #         type='circle',
    #         circle=dict(radius=10),
    #         color='#00f',
    #         # opacity=0.8,
    #         symbol=dict(icon='marker', iconsize=10),
    #     )
    #     layers.append(layer)
    #
    # update_args = dict(center=dict(lat=r.lat, lon=r.lon), layers=layers)
    # if click:
    #     update_args['zoom'] = 15
    # else:
    #     update_args['zoom'] = DEFAULT_ZOOM
    #
    # map_fig.update_mapboxes(**update_args)
    #
    # return map_fig


selected_start_time = None
selected_end_time = None


@app.callback(
    [Output('label-button-output', 'children')],
    [Input('label-buttons', 'value')],
)
def label_values(value):
    if value is None:
        return ['']

    if value == 'none':
        value = None

    query = '''
        WITH updated AS (
            UPDATE trips_ingest_location
                SET manual_atype = %(label)s
                WHERE time >= %(start_time)s AND time <= %(end_time)s
                AND uuid = %(uid)s :: uuid
                RETURNING time
        )
        SELECT
            COUNT(updated.time) AS count,
            MIN(updated.time) AS start_time,
            MAX(updated.time) AS end_time
        FROM updated
    '''
    print('Updating to %s' % value)
    with conn.cursor() as cursor:
        params = dict(
            label=value,
            start_time=selected_start_time,
            end_time=selected_end_time,
            uid=locations_uuid
        )
        cursor.execute(query, params)
        count, start, end = cursor.fetchall()[0]
        d = locations_df
        d.loc[(d.time >= start) & (d.time <= end), 'manual_atype'] = value

    conn.commit()
    print('updated %d rows' % count)

    return ['']


@app.callback(
    [Output('label-button-container', 'children')],
    [Input('time-graph', 'selectedData')],
)
def handle_selection(selection):
    global selected_start_time, selected_end_time

    if not selection:
        return [html.Div(id='label-buttons')]

    start, end = selection['range']['x']
    selected_start_time = LOCAL_TZ.localize(parse(start))
    selected_end_time = LOCAL_TZ.localize(parse(end))

    modes = ['none', 'still', 'on_foot', 'in_vehicle', 'on_bicycle', 'tram', 'bus', 'car', 'train', 'other']
    label_buttons = dbc.FormGroup([
        dbc.RadioItems(
            options=[dict(label=x, value=x) for x in modes],
            id='label-buttons',
            inline=True,
            value=None,
        ),
    ])
    return [html.Div([label_buttons, html.Div(id='label-button-output')])]


def generate_containers(uid, time_fig=None, map_component=None, trip_component=None):
    graph_kwargs = {}
    if time_fig is not None:
        graph_kwargs['figure'] = time_fig

    dev = Device.objects.filter(uuid=uid).first()
    if dev is not None:
        dev_str = '%s %s (%s %s)' % (
            dev.platform, dev.system_version, dev.brand, dev.model
        )
    else:
        dev_str = 'Unknown'

    return [
        html.Div('%s – %s' % (uid, dev_str)),
        dbc.Row([
            dbc.Col([map_component], md=6, id='map-container'),
            dbc.Col([
                dbc.Row(
                    dbc.Col([dcc.Graph(id='time-graph', **graph_kwargs)], md=12),
                ),
                dbc.Row(
                    dbc.Col(id='label-button-container', md=12)
                ),
            ], md=6),
        ]),
        dbc.Row([
            dbc.Col([trip_component], id='trip-container', md=6, style={'height': '450px'}),
            dbc.Col(id='data-table-container', md=6),
        ], className='mt-3'),
    ]


@app.callback(
    Output('output-container', 'children'),
    [Input('path', 'pathname'), Input('filtered-switch', 'value'), Input('show-probs-switch', 'value')]
)
def render_output(new_path, disable_filters, show_probs):
    global map_component, trip_component, locations_df, locations_uuid
    global time_filtered_locations_df
    global filters_enabled

    new_filtered = not disable_filters
    pc = PerfCounter('render_output')

    if new_path:
        new_path = new_path.strip('/')
        new_uid = new_path

    if not new_uid:
        return None

    if locations_uuid is None or locations_uuid != new_uid or filters_enabled != new_filtered:
        pc.display('reading trips for %s' % new_uid)
        df = read_locations(conn, new_uid, include_all=True, start_time='2021-05-20')
        pc.display('trips read (%d rows)' % len(df))
        df.time = pd.to_datetime(df.time, utc=True)

        trip_dfs = []

        for trip_id in df.trip_id.unique():
            trip_df = df[df.trip_id == trip_id].copy()
            if new_filtered and trip_id >= 0:
                pc.display('filtering trip %d' % trip_id)
                trip_df = filter_trips(trip_df)
                pc.display('filtering done')
            #trip_df = split_trip_legs(conn, trip_df)
            trip_dfs.append(trip_df)

        trip_dfs.append(df[df.trip_id == -1])
        df = pd.concat(trip_dfs)
        df = df.sort_values('time')
        df.created_at = df.created_at.dt.tz_convert(LOCAL_TZ)

        filters_enabled = new_filtered

        df['local_time'] = df.time.dt.tz_convert(LOCAL_TZ)
        df['distance'] = df.distance.round(1)
        df['closest_car_way_dist'] = df['closest_car_way_dist'].round(1)
        df['x'] = df.x.round(1)
        df['y'] = df.y.round(1)
        if 'xf' in df:
            df['xf'] = df.xf.round(1)
        if 'yf' in df:
            df['yf'] = df.yf.round(1)
        locations_df = df
        time_filtered_locations_df = df
        locations_uuid = new_uid
    else:
        df = locations_df

    if new_filtered:
        geo = gpd.points_from_xy(df.xf.fillna(df.x), df.yf.fillna(df.y), crs=3067).to_crs(4326)
    else:
        geo = gpd.points_from_xy(df.x, df.y, crs=3067).to_crs(4326)
    df['lon'] = geo.x
    df['lat'] = geo.y

    pc.display('samples processed')
    time_fig = make_subplots(specs=[[{"secondary_y": True}]])
    time_fig.update_yaxes(rangemode='tozero', fixedrange=True)

    # time_fig.update_traces(marker=dict(opacity=0.8))

    mandf = df.copy()
    mandf['manual_atype_changed'] = mandf.manual_atype.shift(1) != mandf.manual_atype
    mandf['shape_id'] = mandf['manual_atype_changed'].cumsum()
    mandf = mandf[~mandf.manual_atype.isna()]
    pc.display('about to generate shapes')
    for shape_id in mandf.shape_id.unique():
        sdf = mandf[mandf.shape_id == shape_id]
        if not sdf.iloc[0].manual_atype:
            continue
        color = COLOR_MAP[sdf.iloc[0].manual_atype]
        d1 = sdf.local_time.min().to_pydatetime()
        d2 = sdf.local_time.max().to_pydatetime()
        time_fig.add_shape(
            type='line', x0=d1, x1=d2, y0=-.2, y1=-.25,
            xref='x', yref='paper',
            line=dict(
                color=color,
                width=4,
            )
        )

    pc.display('shapes generated')

    for mode in COLOR_MAP.keys():
        mdf = df[df.atype == mode]
        if len(mdf):
            time_fig.add_trace(dict(
                type='scattergl', x=mdf.local_time, y=mdf.speed * 3.6, mode='markers', name=mode,
                marker=dict(color=COLOR_MAP[mode], size=8, symbol='circle')
            ))
        if mode in df:
            df[mode] = df[mode].round(2)

    for mode in COLOR_MAP.keys():
        if 'atypef' not in df:
            continue
        cdf = df[df.atypef == mode]
        if len(cdf):
            time_fig.add_trace(dict(
                type='scattergl', x=cdf.local_time, y=cdf.speed * 3.6, mode='markers', name='%s (fix)' % mode,
                marker=dict(color=COLOR_MAP[mode], size=4, symbol='circle')
            ))
    if show_probs:
        for mode in COLOR_MAP.keys():
            if mode not in df:
                continue

            time_fig.add_trace(dict(
                type='scattergl', x=df.local_time, y=df[mode], mode='lines', name=mode,
                connectgaps=False, line=dict(color=COLOR_MAP[mode]),
                opacity=0.7,
            ), secondary_y=True)

    pc.display('traces generated')

    map_component = make_map_component()
    pc.display('map component done')
    trip_component = make_trip_component()
    pc.display('trip component done')

    return generate_containers(new_uid, time_fig, map_component, trip_component)


@app.callback(
    Output('path', 'pathname'),
    [Input('uuid-selector', 'value')]
)
def select_uuid(new_uuid):
    print('new uuid: %s' % new_uuid)
    if new_uuid == locations_uuid:
        raise PreventUpdate
    return new_uuid


def label_for_uuid(uid):
    dev = device_by_uuid.get(uid)
    if not dev:
        return uid
    if dev.friendly_name:
        name_str = ': %s' % dev.friendly_name
    else:
        name_str = ''
    return '%s%s (%s %s, %s %s)' % (uid, name_str, dev.platform, dev.system_version, dev.brand, dev.model)


app.layout = dbc.Container([
    dcc.Location(id='path', refresh=False),
    dbc.Row([
        dbc.Col([
            dbc.FormGroup([
                dbc.Checklist(
                    options=[{"label": "Disable filters", "value": 0}],
                    id='filtered-switch',
                    switch=True,
                ),
                dbc.Checklist(
                    options=[{"label": "Show probabilities", "value": 0}],
                    id='show-probs-switch',
                    switch=True,
                ),
            ]),
        ]),
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Select(
                id="uuid-selector",
                options=[{'label': label_for_uuid(x), 'value': x} for x in uuids],
                value=None,
            )
        ], md=4)
    ]),
    html.Div(
        generate_containers(None),
        id='output-container'
    ),
], fluid=True)


if __name__ == '__main__':
    app.run_server(debug=True)
