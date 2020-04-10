from flask import Flask ,render_template,request
from bokeh.embed import components
from os.path import dirname, join
from bokeh.io import curdoc
from bokeh.plotting import figure
from bokeh.models import Label, GeoJSONDataSource, LinearColorMapper, ColorBar,Dropdown, Select,HoverTool,Panel, Tabs,TapTool,Text
from bokeh.layouts import column, row, widgetbox
from bokeh.palettes import brewer
import geopandas as gpd
import json
import sys
import numpy as np
from flask import jsonify
#reading geodata
# read section_communales shapefile

# create dataset function
def get_filtered_dataset(filter,col):
    gdf =None
    site_facilities_col = None
    if filter == 'commune':
        gdf = gpd.read_file('data/combined/v0_com_data.shp')
    elif filter == 'departement':
        gdf = gpd.read_file('data/combined/v0_dep_data.shp')
    else:
        gdf = gpd.read_file('data/combined/v0_sec_data.shp')
    
    gdf['Hospitals'] = gdf[['HCR', 'HD', 'HU','hop', 'hop_specia']].sum(axis=1)
    if col == 'all':
        site_facilities_col = ['CAL', 'Dispensair', 'Hospitals']
    elif col == 'hosp':
        site_facilities_col = ['Hospitals']
    elif col == 'cal':
        site_facilities_col = ['CAL']
    elif col == 'disp':
        site_facilities_col = ['Dispensair']
    elif col  == 'disp+cal':
        site_facilities_col = ['Dispensair','CAL']
    elif col  == 'hosp+cal':
        site_facilities_col = ['Hospitals','CAL']
    else:
        site_facilities_col = ['Hospitals','Dispensair']

    admin_cols = [col for col in gdf.columns if col not in site_facilities_col+['HCR', 'HD', 'HU','hop', 'hop_specia','Dispensair','CAL','Hospitals']]
    gdf = gdf[admin_cols+site_facilities_col]
    gdf[site_facilities_col] = gdf[site_facilities_col].fillna(0.0)
    gdf['Total_sites'] =gdf[site_facilities_col].sum(axis=1)
    gdf['health_density'] = np.round((gdf['Total_sites']/gdf['IHSI_UNFPA'])*10000,3)
    return gdf
    
map_dict ={'all':'Total des établissements de santé','hosp':'Hopitaux','cal':'Centres de santé avec lits','disp':'Dispensaires','disp+cal':'Dispensaires + Centres de santé avec lits','hosp+cal':'Hopitaux + Centres de santé avec lits','hosp+disp':'Hopitaux + Dispensaires'}






def getDataset(geodata, name, adm_division):
    #name: name of the adm division
    #adm_division: type of adm division
    v=geodata.copy()
    v.set_index(adm_division,inplace=True)
    x=v.loc[name].copy()
    x.reset_index(inplace=True)
    print(x.columns)
    print(x.shape)
    return x

def getGeoSource(gdf):
    merged_json=json.loads(gdf.to_json())
    json_data = json.dumps(merged_json)
    return GeoJSONDataSource(geojson = json_data)


def plot_map(gdf, column=None, title='',tooltip=None):
    #code from https://github.com/dmnfarrell/teaching/blob/master/geo/maps_python.ipynb
    geosource=getGeoSource(gdf)
    palette = brewer['RdYlBu'][10]
    palette = palette[::-1]
    vals = gdf[column]
    
       #Instantiate LinearColorMapper that linearly maps numbers in a range, into a sequence of colors.
    color_mapper = LinearColorMapper(palette = palette, low = vals.min(), high = vals.max())
    color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8, width=500, height=20, 
                         location=(0,0), orientation='horizontal')
    p1 = figure(title=title)
    p1.axis.visible = False
    p1.xgrid.visible = False
    p1.ygrid.visible = False
    p1.patches('xs','ys',source=geosource, line_color = "white", line_width =1, fill_alpha = 0.8,
               fill_color={'field' :column , 'transform': color_mapper},)
    TOOLTIPS = tooltip
    p1.width = 1000
    p1.height = 850
    p1.add_tools(HoverTool(tooltips=TOOLTIPS))
    p1.add_layout(color_bar, 'above')
    return p1

sectiontool=[   ("Departement","@ADM1_FR"),
                ("Commune","@ADM2_FR"),
                ("Section commune","@ADM3_FR"),
                ("Population","@IHSI_UNFPA"),
                ("Nombre de sites","@Total_sites"),
                ("Nombre de dispensaires","@Dispensair"),
                ("Nombre d'hopitaux ","@Hospitals"),
                ("Nombre de centres de santé avec lits ","@CAL"),
                ]


app = Flask(__name__)

@app.route('/',methods=['GET', 'POST'])
def index():
   gdf2 = get_filtered_dataset('departement','all')
   gdf2['Total_sites'] = gdf2['Total_sites'].astype('int')
   gdf2['IHSI_UNFPA']=gdf2['IHSI_UNFPA'].astype('int')
   gdf = None
   division = 'commune'
   etablissement ='all'
   if request.method == 'POST':
       division = request.form['division'] 
       etablissement =request.form['etablissement']
      # fourth
       gdf = get_filtered_dataset(division,etablissement)
   else :
        gdf = get_filtered_dataset(division,etablissement)
       
   p3=plot_map(gdf = gdf,column="Total_sites",title=map_dict[etablissement]+ ' par '+ division,tooltip=sectiontool )
   script, div = components(p3)
   div.replace('class="bk-root"','class="bk-root col-12 style="height: 100%')
   
   return render_template("index.html", script=script, div=div,division=division, etablissement =etablissement,gdf2=gdf2)
   

@app.route("/commune/<dept_name>")
def commune_list (dept_name):
    if dept_name == 'all':
        return jsonify(None)

    commune = dict(name = list(set(data_gpd['ADM2_FR'][data_gpd['ADM1_FR'] == dept_name])))
    return jsonify(commune)

if __name__ == '__main__':
	app.run(port=5000, debug=True)

# with your other routes...
