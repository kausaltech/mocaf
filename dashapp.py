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


def read_uuids():
    with eng.connect() as conn:
        print('Reading uids')
        res = conn.execute(f'SELECT uuid, count(id) AS count FROM {TABLE_NAME} WHERE aconf IS NOT NULL GROUP BY uuid ORDER BY count DESC LIMIT 100');
        rows = res.fetchall()
        uuids = [str(row[0]) for row in rows]
    return uuids


try:
    uuids = [x.strip() for x in open('uuids.txt', 'r').readlines()]
except FileNotFoundError:
    open('uuids.txt', 'w').write('\n'.join(read_uuids()))


def read_locations(uid):
    print('Selected UID %s. Reading dataframe.' % uid)
    with eng.connect() as conn:
        df = pd.read_sql_query(f"""
            SELECT
                time,
                ST_X(ST_Transform(loc, 3067)) AS x,
                ST_Y(ST_Transform(loc, 3067)) AS y,
                acc,
                atype,
                aconf,
                speed,
                heading
            FROM {TABLE_NAME} WHERE uuid = '%s'::uuid ORDER BY time
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

@app.callback(
    Output('map-graph', 'figure'),
    [Input('time-graph', 'hoverData'), Input('time-graph', 'clickData')])
def display_hover_data(hoverData, clickData):
    if not hoverData and not clickData:
        return map_fig

    if clickData:
        click = True
    else:
        click = False

    layers = []
    for p in hoverData['points']:
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

    map_fig = px.scatter_mapbox(
        gdf, lat="lat", lon="lon", color='atype', zoom=DEFAULT_ZOOM,
        height=400, hover_data=['atype', 'speed', 'acc'], size='size', size_max=5
    )
    map_fig.update_layout(mapbox_style="open-street-map", margin={'l': 0, 'b': 0, 'r': 0, 't': 10})

    time_fig = px.scatter(gdf, x='datetime', y='speed', color='atype', hover_data=['acc'])

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
