import os
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine


from dotenv import load_dotenv
load_dotenv()

TABLE_NAME = 'trips_location'
DEFAULT_ZOOM = 12

eng = create_engine(os.getenv('DATABASE_URL'))

COLOR_MAP = {
    'still': '#073b4c',
    'walking': '#ffd166',
    'in_vehicle': '#ef476f',
    'running': '#f77f00',
    'on_bicycle': '#06d6a0',
}

def read_uuids():
    with eng.connect() as conn:
        print('Reading uids')
        res = conn.execute(f"""
            SELECT uuid, count(id) AS count FROM {TABLE_NAME}
                WHERE aconf IS NOT NULL AND time >= now() - interval '14 days'
                GROUP BY uuid
                ORDER BY count
                DESC LIMIT 100
        """);
        rows = res.fetchall()
        uuid_counts = ['%s,%s' % (str(row[0]), row[1]) for row in rows]
    print(uuid_counts)
    return uuid_counts


try:
    uuids = [x.split(',')[0].strip() for x in open('uuids.txt', 'r').readlines()]
except FileNotFoundError:
    s = read_uuids()
    open('uuids.txt', 'w').write('\n'.join(s))
    uuids = [x.split(',')[0].strip() for x in s]


def read_locations(uid):
    print('Selected UID %s. Reading dataframe.' % uid)
    with eng.connect() as conn:
        df = pd.read_sql_query(f"""
            SELECT
                time,
                ST_X(ST_Transform(loc, 3067)) AS x,
                ST_Y(ST_Transform(loc, 3067)) AS y,
                loc_error,
                atype,
                aconf,
                speed,
                heading
            FROM {TABLE_NAME}
            WHERE uuid = '%s'::uuid AND time >= now() - interval '14 days'
            ORDER BY time
        """ % uid, conn)

    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.x, df.y, crs='epsg:3067'))
    gdf = gdf.to_crs('EPSG:4326')
    gdf['lat'] = gdf.geometry.y
    gdf['lon'] = gdf.geometry.x
    gdf['size'] = 1

    gdf['datetime'] = pd.to_datetime(gdf.time)
    gdf['speed'] *= 3.6
    print(gdf)

    return gdf

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
px.set_mapbox_access_token(os.getenv('MAPBOX_ACCESS_TOKEN'))

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

map_fig = None
gdf = None


def make_map_fig(xstart=None, xend=None):
    df = gdf
    if xstart and xend:
        df = df[(df.datetime >= xstart) & (df.datetime <= xend)]

    fig = px.scatter_mapbox(
        df, lat="lat", lon="lon", color='atype', zoom=DEFAULT_ZOOM,
        height=400, hover_data=['atype', 'speed', 'loc_error'], size='size', size_max=5,
        color_discrete_map=COLOR_MAP,
    )
    fig.update_layout(mapbox_style="open-street-map", margin={'l': 0, 'b': 0, 'r': 0, 't': 10})
    return fig


@app.callback(
    Output('map-graph', 'figure'),
    [Input('time-graph', 'hoverData'), Input('time-graph', 'clickData'), Input('time-graph', 'relayoutData')])
def display_hover_data(hover_data, click_data, relayout_data):
    global map_fig

    if relayout_data and 'xaxis.range[0]' in relayout_data:
        map_fig = make_map_fig(relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]'])

    if not hover_data and not click_data:
        return map_fig

    if click_data:
        click = True
    else:
        click = False

    layers = []
    for p in hover_data['points']:
        trace = map_fig['data'][p['curveNumber']]
        r = gdf.loc[gdf.datetime == p['x']].iloc[0]
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
    [Input('uuid-selector', 'value')]
)
def handle_uuid_selection(new_uid):
    global map_fig, gdf

    if not new_uid:
        return None
    gdf = read_locations(new_uid)

    map_fig = make_map_fig()
    time_fig = px.scatter(
        gdf, x='datetime', y='speed', color='atype', hover_data=['loc_error'],
        color_discrete_map=COLOR_MAP,
    )

    return [
        dbc.Col(dcc.Graph(id='map-graph', figure=map_fig), md=6),
        dbc.Col(dcc.Graph(id='time-graph', figure=time_fig), md=6),
    ]


app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dbc.Select(
                id="uuid-selector",
                options=[{'label': x, 'value': x} for x in uuids]
            )
        ], md=4)
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='map-graph'), md=6),
        dbc.Col(dcc.Graph(id='time-graph'), md=6),
    ], id='graph-container'),
], fluid=True)

if __name__ == '__main__':
    app.run_server(debug=True)
