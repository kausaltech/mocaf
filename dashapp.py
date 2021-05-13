import os
import dash
import dash_deck
import dash_table
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
from calc.trips import filter_trips, read_trips, read_uuids


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
    'tram': '#ef476f',
    'bus': '#ef476f',
    'car': '#ef476f',
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
    return colors + [250]


COLOR_MAP_RGB = {atype: hex_to_rgba(color) for atype, color in COLOR_MAP.items()}


locations_df = None
locations_uuid = None
time_filtered_locations_df = None
map_component = None
trip_component = None
data_table_component = None

conn = eng.connect()
uuids = read_uuids(conn.connection)
if DEFAULT_UUID and DEFAULT_UUID not in uuids:
    uuids.insert(0, DEFAULT_UUID)


def make_map_component(xstart=None, xend=None):
    PerfCounter('make_map_fig')

    df = time_filtered_locations_df.copy()

    df['color'] = df['atype'].map(COLOR_MAP_RGB)
    df.loc_error = df.loc_error.fillna(value=-1)
    df.aconf = df.aconf.fillna(value=-1)
    df['time_str'] = df.local_time.astype(str)
    df.speed = df.speed.fillna(value=-1)
    df = df.dropna()
    df = df[['lon', 'lat', 'loc_error', 'color', 'aconf', 'speed', 'time_str', 'atype']]
    layer = pydeck.Layer(
        'PointCloudLayer',
        df,
        # get_position=['lon', 'lat', 'speed'],
        get_position=['lon', 'lat'],
        auto_highlight=True,
        get_radius='loc_error < 20 ? loc_error * 1.5 : 20 * 1.5',
        get_color='color',
        pickable=True,
        point_size=5,
    )

    initial_view_state = pydeck.data_utils.viewport_helpers.compute_view(df)

    TOOLTIP_TEXT = {
        'html': '{time_str}<br />{atype}<br />Speed: {speed} km/h'
    }

    r = pydeck.Deck(
        layers=[layer],
        initial_view_state=initial_view_state,
        # map_provider='mapbox',
        map_style='road')
    # print(r.to_json())
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
    print(device)
    if not device:
        return None

    trips = device.trips.all()
    df = time_filtered_locations_df
    start = df['local_time'].min()
    end = df['local_time'].max()
    trips = trips.started_during(start, end)
    print('%d trips' % len(trips))

    recs = []
    for trip in trips:
        for leg in trip.legs.all():
            path = [[p.x, p.y] for p in leg.locations.values_list('loc', flat=True)]
            name = 'Trip %d - %s' % (trip.id, leg.mode.name)
            color = hex_to_rgb(TRANSPORT_COLOR_MAP.get(leg.mode.identifier, '#aaaaaa'))
            recs.append(dict(
                name=name, color=color, path=path,
                start_time=leg.start_time.astimezone(LOCAL_TZ).isoformat(),
                end_time=leg.end_time.astimezone(LOCAL_TZ).isoformat(),
            ))

    initial_view_state = pydeck.data_utils.viewport_helpers.compute_view(df[['lon', 'lat']])

    paths_df = pd.DataFrame.from_records(recs)

    layer = pydeck.Layer(
        type='PathLayer',
        data=paths_df,
        pickable=True,
        get_color='color',
        # width_scale=20,
        width_min_pixels=2,
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
        map_style='road'
    )
    dc = dash_deck.DeckGL(
        data=r.to_json(), id="deck-gl-trips", mapboxKey=os.getenv('MAPBOX_ACCESS_TOKEN'),
        tooltip=TOOLTIP_TEXT, enableEvents=['click'],
    )

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
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)


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
        return map_component, trip_component, data_table_component

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

    with eng.connect() as conn:
        print('Updating to %s' % value)
        ret = conn.execute('''
            UPDATE trips_ingest_location
                SET manual_atype = %(label)s
                WHERE time >= %(start_time)s AND time <= %(end_time)s
                AND uuid = %(uid)s :: uuid
        ''', dict(label=value, start_time=selected_start_time, end_time=selected_end_time, uid=locations_uuid))
        print('done')

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

    modes = ['none', 'still', 'on_foot', 'in_vehicle', 'on_bicycle', 'tram', 'bus', 'car']
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
    [Input('path', 'pathname'), Input('uuid-selector', 'value'), Input('filtered-switch', 'value')]
)
def render_output(new_path, new_uid, filtered):
    global map_component, trip_component, locations_df, locations_uuid
    global time_filtered_locations_df

    pc = PerfCounter('render_output')

    if not new_uid:
        if new_path:
            new_path = new_path.strip('/')
        new_uid = new_path

    if not new_uid:
        return None

    if locations_uuid is None or locations_uuid != new_uid:
        df = read_trips(eng, new_uid, include_all=True)
        pc.display('trips read')
        df.time = pd.to_datetime(df.time, utc=True)
        print('filtering')
        df = filter_trips(df)
        # df['speed'] *= 3.6
        # print('done')
        df['local_time'] = df.time.dt.tz_convert(LOCAL_TZ)
        df['distance'] = df.distance.round(1)
        df['x'] = df.x.round(1)
        df['y'] = df.y.round(1)
        locations_df = df
        time_filtered_locations_df = df
        locations_uuid = new_uid
    else:
        df = locations_df

    print(df.tail(20))

    if filtered is not None and len(filtered):
        geo = gpd.points_from_xy(df.xf, df.yf, crs=3067).to_crs(4326)
    else:
        geo = gpd.points_from_xy(df.x, df.y, crs=3067).to_crs(4326)
    df['lon'] = geo.x
    df['lat'] = geo.y

    pc.display('samples processed')
    time_fig = make_subplots(specs=[[{"secondary_y": True}]])
    time_fig.update_yaxes(rangemode='tozero', fixedrange=True)

    time_fig.update_traces(marker=dict(opacity=0.5))
    for mode in COLOR_MAP.keys():
        mdf = df[df.atype == mode]
        if not len(df):
            continue

        time_fig.add_trace(dict(
            type='scattergl', x=mdf.local_time, y=mdf.speed * 3.6, mode='markers', name=mode,
            marker=dict(color=COLOR_MAP[mode], symbol='circle')
        ))

        #mandf = df[df.manual_atype == mode]
        #time_fig.add_trace(dict(
        #    type='scattergl', x=mandf.local_time, y=mandf.speed * 3.6, mode='markers', name=mode,
        #    marker=dict(color=COLOR_MAP[mode], symbol='x-open')
        #))
        if mode in df:
            time_fig.add_trace(dict(
                type='scattergl', x=df.local_time, y=df[mode], mode='lines', name=mode,
                connectgaps=False, line=dict(color=COLOR_MAP[mode])
            ), secondary_y=True)

    pc.display('traces generated')

    map_component = make_map_component()
    pc.display('map component done')
    trip_component = make_trip_component()
    pc.display('trip component done')

    return generate_containers(new_uid, time_fig, map_component, trip_component)


app.layout = dbc.Container([
    dcc.Location(id='path', refresh=False),
    dbc.Row([
        dbc.Col([
            dbc.FormGroup([
                dbc.Checklist(
                    options=[{"label": "Filtered", "value": 0}],
                    id='filtered-switch',
                    switch=True,
                ),
            ]),
        ]),
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Select(
                id="uuid-selector",
                options=[{'label': x, 'value': x} for x in uuids],
                value=DEFAULT_UUID or None,
            )
        ], md=4)
    ]),
    html.Div(
        generate_containers(DEFAULT_UUID),
        id='output-container'
    ),
], fluid=True)


if __name__ == '__main__':
    app.run_server(debug=True)
