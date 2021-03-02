import os
import dash
import dash_deck
import pydeck
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine

from utils.perf import PerfCounter
from calc.trips import read_trips, read_uuids

from dotenv import load_dotenv
load_dotenv()

DEFAULT_ZOOM = 12
DEFAULT_UUID = os.getenv('DEFAULT_UUID')

eng = create_engine(os.getenv('DATABASE_URL'))


COLOR_MAP = {
    'still': '#073b4c',
    'walking': '#ffd166',
    'on_foot': '#ffd166',
    'in_vehicle': '#ef476f',
    'running': '#f77f00',
    'on_bicycle': '#06d6a0',
    'unknown': '#cccccc',
}


def hex_to_rgba(value):
    value = value.lstrip('#')
    lv = len(value)
    colors = list(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
    return colors + [250]


COLOR_MAP_RGB = {atype: hex_to_rgba(color) for atype, color in COLOR_MAP.items()}


locations_df = None
map_component = None
uuids = read_uuids(eng)
if DEFAULT_UUID and DEFAULT_UUID not in uuids:
    uuids.insert(0, DEFAULT_UUID)


def make_map_component(xstart=None, xend=None):
    pc = PerfCounter('make_map_fig')

    df = locations_df.copy()

    if xstart and xend:
        df = df[(df.time >= xstart) & (df.time <= xend)]

    df['color'] = df['atype'].map(COLOR_MAP_RGB)
    df.loc_error = df.loc_error.fillna(value=-1)
    df.aconf = df.aconf.fillna(value=-1)

    min_time = df.time.min()
    max_time = df.time.max()
    diff = (max_time - min_time).total_seconds()
    if False and diff < 60 * 3600:
        df['timestamp'] = ((df.time - min_time).dt.total_seconds() * 1000).astype(int)
        df = df[['lon', 'lat', 'loc_error', 'color', 'aconf', 'timestamp']]
        layer = pydeck.Layer(
            'TripsLayer',
            df,
            get_position=['lon', 'lat'],
            auto_highlight=True,
            get_radius='loc_error < 20 ? loc_error : 20',
            get_fill_color='color',
            pickable=True,
        )
    else:
        df = df[['lon', 'lat', 'loc_error', 'color', 'aconf']]
        layer = pydeck.Layer(
            'ScatterplotLayer',
            df,
            get_position=['lon', 'lat'],
            auto_highlight=True,
            get_radius='loc_error < 20 ? loc_error * 1.5 : 20 * 1.5',
            get_fill_color='color',
            pickable=True,
        )

    initial_view_state = pydeck.data_utils.viewport_helpers.compute_view(df)

    r = pydeck.Deck(
        layers=[layer],
        initial_view_state=initial_view_state,
        # map_provider='mapbox',
        map_style='road')
    # print(r.to_json())
    dc = dash_deck.DeckGL(data=r.to_json(), id="deck-gl", mapboxKey=os.getenv('MAPBOX_ACCESS_TOKEN'))

    return dc


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
px.set_mapbox_access_token(os.getenv('MAPBOX_ACCESS_TOKEN'))
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])


@app.callback(
    Output('map-container', 'children'),
    [Input('time-graph', 'hoverData'), Input('time-graph', 'clickData'), Input('time-graph', 'relayoutData')])
def display_hover_data(hover_data, click_data, relayout_data):
    global map_component

    if relayout_data and 'xaxis.range[0]' in relayout_data:
        map_component = make_map_component(
            relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']
        )

    return map_component

    if not hover_data and not click_data:
        return map_fig

    if click_data:
        click = True
    else:
        click = False

    layers = []
    df = locations_df
    for p in hover_data['points']:
        trace = map_fig['data'][p['curveNumber']]
        r = df.loc[df.time == p['x']].iloc[0]
        layer = dict(
            sourcetype='geojson',
            source={
                'type': 'Feature',
                "properties": {},
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(r.lon), float(r.lat)]
                },
            },
            type='circle',
            circle=dict(radius=10),
            color='#00f',
            # opacity=0.8,
            symbol=dict(icon='marker', iconsize=10),
        )
        layers.append(layer)

    update_args = dict(center=dict(lat=r.lat, lon=r.lon), layers=layers)
    if click:
        update_args['zoom'] = 15
    else:
        update_args['zoom'] = DEFAULT_ZOOM

    map_fig.update_mapboxes(**update_args)

    return map_fig


@app.callback(
    Output('graph-container', 'children'),
    [Input('path', 'pathname'), Input('uuid-selector', 'value')]
)
def render_graphs(new_path, new_uid):
    global map_component, locations_df

    if not new_uid:
        if new_path:
            new_path = new_path.strip('/')
        new_uid = new_path

    if not new_uid:
        return None

    locations_df = read_trips(eng, new_uid)

    time_fig = px.scatter(
        locations_df, x='time', y='speed', color='atype',
        hover_data=['trip_id', 'loc_error', 'heading', 'aconf'],
        color_discrete_map=COLOR_MAP,
    )

    map_component = make_map_component()

    return [
        html.Div(new_uid),
        dbc.Row([
            dbc.Col([map_component], md=6, id='map-container'),
            dbc.Col(dcc.Graph(id='time-graph', figure=time_fig), md=6),
        ]),
    ]


app.layout = dbc.Container([
    dcc.Location(id='path', refresh=False),
    dbc.Row([
        dbc.Col([
            dbc.Select(
                id="uuid-selector",
                options=[{'label': x, 'value': x} for x in uuids],
                value=DEFAULT_UUID or None,
            )
        ], md=4)
    ]),
    html.Div([
        dbc.Row([
            dbc.Col(id='map-container', md=6),
            dbc.Col(dcc.Graph(id='time-graph'), md=6),
        ]),
    ], id='graph-container'),
], fluid=True)

if __name__ == '__main__':
    app.run_server(debug=True)
