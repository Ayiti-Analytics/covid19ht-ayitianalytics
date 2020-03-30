# import flask librairy
from flask import Flask,render_template

# import pandas pd
import pandas as pd
# import folium for geomapping
import folium 

pd_pop_adm1 = pd.read_excel('./datasets/hti_adminboundaries_tabulardata.xlsx',sheet_name ='hti_pop2019_adm1',encoding ='utf-16')
pd_pop_adm2 = pd.read_excel('./datasets/hti_adminboundaries_tabulardata.xlsx',sheet_name ='hti_pop2019_adm2',encoding ='utf-16')
pd_pop_adm3 = pd.read_excel('./datasets/hti_adminboundaries_tabulardata.xlsx',sheet_name ='hti_pop2019_adm3',encoding ='utf-16')

# definition of the boundaries in the map
coummune_geo = r'./datasets/commune.geojson'
  
# calculating total number of incidents per district
commune2 = pd.DataFrame(pd_pop_adm2['adm2code'].value_counts().astype(float))
commune2 = commune2.reset_index()
commune2.columns = ['adm2code', 'Number']
coord_ht = (18.788304610553055,-72.23655910919523)
m = folium.Map(
    location=coord_ht,
    tiles='Mapbox Bright',
    zoom_start=8.4 # Limited levels of zoom for free Mapbox tiles.
)

folium.Choropleth(
    geo_data=coummune_geo,
    data=pd_pop_adm2,
    columns= ['adm2code', 'IHSI_UNFPA_2019'],
    key_on='feature.properties.ADM2_PCODE',
    fill_color='Oranges',
    fill_opacity=0.7,
    line_opacity=0.5,
    legend_name='Population',
    reset=True
).add_to(m)

# use flask module
app = Flask(__name__)
 

# define default route
@app.route('/')
def map():
    m.save('templates/map.html')
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)