import os
import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import pandas as pd
import geopandas as gpd

from dotenv import load_dotenv
load_dotenv()


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
px.set_mapbox_access_token(os.getenv('MAPBOX_ACCESS_TOKEN'))

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

DEFAULT_ZOOM = 12

df = pd.read_pickle('trajstuff.pickle')
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.x2, df.y2, crs='epsg:3857'))
gdf = gdf.to_crs('EPSG:4326')
gdf['lat'] = gdf.geometry.y
gdf['lon'] = gdf.geometry.x
gdf['size'] = 1
gdf['datetime'] = pd.to_datetime(gdf.time.astype(int), unit='s')
#gdf.iloc[100]['highlighted'] = 1

map_fig = px.scatter_mapbox(
    gdf, lat="lat", lon="lon", color='atype', zoom=DEFAULT_ZOOM, height=400, hover_data=['atype', 'speed', 'acc'], size='size', size_max=5
)
map_fig.update_layout(mapbox_style="open-street-map", margin={'l': 0, 'b': 0, 'r': 0, 't': 10})

time_fig = px.scatter(gdf, x='datetime', y='speed', color='atype', hover_data=['acc'])


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

    m_size = map_fig['data'][0]['marker']['size']
    m_idxs = gdf.index[gdf.time.isin(x_vals)]
    print(map_fig)
    for i in m_idxs:
        m_size[i] = 2
    """
    #map_fig.loc[map_fig.time.isin(x_vals), 'size'] = 3
    #map_fig.loc[~map_fig.time.isin(x_vals), 'size'] = 1
    """

    return map_fig


app.layout = html.Div(children=[
    dcc.Graph(
        id='map-graph',
        figure=map_fig
    ),
    dcc.Graph(
        id='time-graph',
        figure=time_fig
    )
])

if __name__ == '__main__':
    app.run_server(debug=True)
