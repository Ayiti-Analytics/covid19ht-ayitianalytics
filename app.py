# import flask librairy
from flask import Flask, render_template
import psycopg2
# import pandas pd
import pandas as pd
# import folium for geomapping
import folium
import geopandas as gpd
import numpy as np
from sqlalchemy import create_engine
import os

# pd_pop_adm1 = pd.read_excel('./datasets/hti_adminboundaries_tabulardata.xlsx',sheet_name ='hti_pop2019_adm1',encoding ='utf-16')
# pd_pop_adm2 = pd.read_excel('./datasets/hti_adminboundaries_tabulardata.xlsx',sheet_name ='hti_pop2019_adm2',encoding ='utf-16')
# pd_pop_adm3 = pd.read_excel('./datasets/hti_adminboundaries_tabulardata.xlsx',sheet_name ='hti_pop2019_adm3',encoding ='utf-16')

# definition of the boundaries in the map
# coummune_geo = r'./datasets/commune.geojson'
  
# calculating total number of incidents per district
# commune2 = pd.DataFrame(pd_pop_adm2['adm2code'].value_counts().astype(float))
# commune2 = commune2.reset_index()
# commune2.columns = ['adm2code', 'Number']
# coord_ht = (18.788304610553055,-72.23655910919523)
# m = folium.Map(
#    location=coord_ht,
 #   tiles='Mapbox Bright',
 #   zoom_start=8.4 # Limited levels of zoom for free Mapbox tiles.
#)

#folium.Choropleth(
    #geo_data=coummune_geo,
    #data=pd_pop_adm2,
    #columns= ['adm2code', 'IHSI_UNFPA_2019'],
    #key_on='feature.properties.ADM2_PCODE',
    #fill_color='Oranges',
    #fill_opacity=0.7,
    #line_opacity=0.5,
    #legend_name='Population',
   # reset=True
#).add_to(m)
#reading  section communales geodata

# read sections communales shapefiles
sections_gpd = gpd.read_file('data/combined/v0_sec_data.shp')
sections_gpd.set_geometry('geometry')

# computing long,lat for each secton communale  using centroid function
sections_gpd['x'] = sections_gpd.geometry.centroid.x
sections_gpd['y'] = sections_gpd.geometry.centroid.y

# convert section communale geodataframe to geojson
sections_gpd.to_file("output/section_com.geojson", driver='GeoJSON')

# selecting features needed
features_selected_level3 = [column for column in sections_gpd.columns if column not in ['Shape_Leng','Shape_Area','geometry']]

# computing the population /hospital density
# selecting columns needed
hospital_features = ['CAL', 'Dispensair', 'HCR', 'HD', 'HU', 'hop', 'hop_specia','ADM3_EN']
# compute the total of hospitals
sections_gpd['Total hopitals'] = sections_gpd[hospital_features].sum(axis = 1)
# replace 0 by 0.000000001  to manages infinity values
sections_gpd.loc[sections_gpd['Total hopitals'] == 0, 'Total hopitals'] = 0.000000001
#  density  (1k people)
sections_gpd['IHSI_UNFPA/Total hopitals'] = np.round(sections_gpd['IHSI_UNFPA']/sections_gpd['Total hopitals']/1000.0, 2)

sections_gpd.IHSI_UNFPA = sections_gpd.IHSI_UNFPA / 1000.0
mymap = folium.Map(location=[sections_gpd.y.mean(), sections_gpd.x.mean()], start_zoom=7, tiles=None)
folium.TileLayer('CartoDB positron', name="Light Map", control=False).add_to(mymap)
bins = np.linspace(sections_gpd['IHSI_UNFPA/Total hopitals'].min(), sections_gpd['IHSI_UNFPA/Total hopitals'].max(), 10)
myscale = (sections_gpd['IHSI_UNFPA/Total hopitals'].quantile((0, .25, 0.5, 0.75, 1))).tolist()
mymap.choropleth(
    geo_data='output/section_com.geojson',
    name='density ',
    data=sections_gpd,
    columns=['ADM3_EN', 'IHSI_UNFPA/Total hopitals'],
    key_on="feature.properties.ADM3_EN",
    fill_color='YlOrRd',

    threshold_scale=myscale,
    fill_opacity=0.8,
    line_opacity=0.2,
    legend_name='',
    smooth_factor=0
)

style_function = lambda x: {'fillColor': '#ffffff',
                            'color':'#000000',
                            'fillOpacity': 0.1,
                            'weight': 0.1}
highlight_function = lambda x: {'fillColor': '#000000',
                                'color':'#000000',
                                'fillOpacity': 0.50,
                                'weight': 0.1}
sec = folium.features.GeoJson(
    'output/section_com.geojson',
    style_function=style_function,
    control=True,
    highlight_function=highlight_function,
    tooltip=folium.features.GeoJsonTooltip(
        fields=['ADM3_EN','IHSI_UNFPA','CAL', 'Dispensair', 'HCR', 'HD', 'HU', 'hop', 'hop_specia'],
        aliases=['Section communales: ','Nombre de personnes','CAL','Dispensaire','Hopital communautaire de reference','Hopital D.','Hopital universitaire','Hopital','Hopital Specialise'],
        style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")
    )
)
mymap.add_child(sec)
mymap.keep_in_front(sec)
folium.LayerControl(name ='essaa').add_to(mymap)
mymap

## Database parametter connection
def get_posgres_connection():
    db_name = os.getenv("PSQL_DB_NAME")
    db_user = os.getenv("PSQL_DB_USER")
    db_password = os.getenv("PSQL_DB_PASSWORD")
    db_host = os.getenv("PSQL_DB_HOST")
    sql_engine = create_engine(f'postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}')
    return sql_engine



# use flask module
app = Flask(__name__)
 

# define default route
@app.route('/')
def map():
    mymap.save('templates/map.html')
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)

#export PSQL_DB_HOST="haiti-data.cgz5ttlgvxan.us-east-2.rds.amazonaws.com"
#export PSQL_DB_USER="ayiti"
#export PSQL_DB_PASSWORD="pasgenprobleme"
#export PSQL_DB_NAME="postgres"
