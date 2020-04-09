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
com_gpd = gpd.read_file('data/combined/v0_com_data.shp')
print(com_gpd.head().columns)
#'CAL', 'CSL', 'Dispensair', 'HCR', 'HD', 'HU','hop', 'hop_specia'
site_facilities_col = ['ADM1_FR','ADM2_FR','CAL', 'Dispensair', 'HCR', 'HD', 'HU','hop', 'hop_specia']

# Compute the total of sites
com_gpd['Total_sites'] = com_gpd[site_facilities_col].sum(axis=1)
com_gpd['Hospitals'] = com_gpd[['HCR', 'HD', 'HU','hop', 'hop_specia']].sum(axis=1)
data_gpd = com_gpd[['IHSI_UNFPA','Hospitals']+site_facilities_col+['Total_sites','geometry']].copy()
data_gpd.set_geometry('geometry')
# Evaluate the density of (Number of health facilities / Total population in a designated area)
data_gpd['health_density'] = (com_gpd['Total_sites']/com_gpd['IHSI_UNFPA'])*10000
data_gpd['health_density'].astype(np.float32)
data_gpd.loc[data_gpd['health_density'] == 0.0,'health_density'] = 0.001
data_gpd['health_density'] = np.log(data_gpd['health_density'])

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


def plot_map(gdf,val, column=None, title='',tooltip=None):
    #code from https://github.com/dmnfarrell/teaching/blob/master/geo/maps_python.ipynb
    geosource=getGeoSource(val)
    palette = brewer['RdYlBu'][8]
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
    p1.patches('xs','ys',source=geosource, line_color = "black", line_width = 0.25, fill_alpha = 1,
               fill_color={'field' :column , 'transform': color_mapper},)
    TOOLTIPS = tooltip
    p1.width = 1000
    p1.height = 700
    p1.add_tools(HoverTool(tooltips=TOOLTIPS))
    p1.add_layout(color_bar, 'below')
    return p1

sectiontool=[   ("Departement","@ADM1_FR"),
                ("Commune","@ADM2_FR"),
                ("Population","@IHSI_UNFPA"),
                ("Nombre de sites","@Total_sites"),
                ("Nombre de dispensaires","@Dispensair"),
                ("Nombre d'hopitaux ","@Hospitals"),
                ("Nombre de centres de santé avec lits ","@CAL"),
                ]


app = Flask(__name__)

@app.route('/',methods=['GET', 'POST'])
def index():
   dept = dict(name = list(set(data_gpd['ADM1_FR'])))
   dept_name = 'all'
   col = []
   hosp_checked, disp_checked, cal_checked = 0, 0, 0
   if request.method == 'POST':
       dept_name = request.form['departement'] 
      # fourth
    
      
       
   val = data_gpd.copy()
   if dept_name != 'all':
       val = data_gpd[data_gpd['ADM1_FR'] == dept_name ].copy()        
   p3=plot_map(val=val,gdf = data_gpd,column="health_density",title=" Hopital par 10000 habitants",tooltip=sectiontool )
   script, div = components(p3)
   
   return render_template("index.html", script=script, div=div,dept=dept, dept_name =dept_name,hosp_checked=hosp_checked,disp_checked=disp_checked,cal_checked=cal_checked)
   

@app.route("/commune/<dept_name>")
def commune_list (dept_name):
    if dept_name == 'all':
        return jsonify(None)

    commune = dict(name = list(set(data_gpd['ADM2_FR'][data_gpd['ADM1_FR'] == dept_name])))
    return jsonify(commune)

if __name__ == '__main__':
	app.run(port=5000, debug=True)

# with your other routes...
