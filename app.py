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
from flask_cors import CORS
import pandas as pd
#reading geodata
# read section_communales shapefile
# create dataset function

# this function return a geodataframe by filtering data by admin division and health sites facililites
### Owner Yvel Marcelin
def get_filtered_dataset(filter,col):
    # section tools helps to know which columns to display on the map
    sectiontool=[]
    # initalize the geo dataframe
    gdf =None
    # initialize health sites facililites 
    site_facilities_col = None
  
   # selects the matched admin division boundary 
    if filter == 'commune':
        gdf = gpd.read_file('data/combined/v0_com_data.shp')
        sectiontool.append( ("Departement","@ADM1_FR"))
        sectiontool.append(("Commune","@ADM2_FR"))
    elif filter == 'departement':
        gdf = gpd.read_file('data/combined/v0_dep_data.shp')
        sectiontool.append( ("Departement","@ADM1_FR"))
    elif filter == 'section communale':
        gdf = gpd.read_file('data/combined/v0_sec_data.shp')
        sectiontool.append( ("Departement","@ADM1_FR"))
        sectiontool.append(("Commune","@ADM2_FR"))
        sectiontool.append(("Section commune","@ADM3_FR"))

    # sum all the hospitals 
    gdf['Hospitals'] = gdf[['HCR', 'HD', 'HU','hop', 'hop_specia']].sum(axis=1)

    # selects health site facililites
    if col == 'all':
        site_facilities_col = ['CAL', 'Dispensair', 'Hospitals']
        sectiontool.append(("Nombre de dispensaires","@Dispensair"))
        sectiontool.append( ("Nombre d'hopitaux ","@Hospitals"))
        sectiontool.append( ("Nombre de centres de santé avec lits ","@CAL"))
    elif col == 'hosp':
        site_facilities_col = ['Hospitals']
        sectiontool.append( ("Nombre d'hopitaux ","@Hospitals"))
       
    elif col == 'cal':
        site_facilities_col = ['CAL']
        sectiontool.append( ("Nombre de centres de santé avec lits ","@CAL"))
    elif col == 'disp':
        site_facilities_col = ['Dispensair']
        sectiontool.append(("Nombre de dispensaires","@Dispensair"))
   
    # selects non site facilities columns
    admin_cols = [col for col in gdf.columns if col not in site_facilities_col+['HCR', 'HD', 'HU','hop', 'hop_specia','Dispensair','CAL','Hospitals']]
     # selects columns needed to display on the map
    gdf = gdf[admin_cols+site_facilities_col]
    # fill na values by 0.0
    gdf[site_facilities_col] = gdf[site_facilities_col].fillna(0.0)
    # sum the total health site facilities
    gdf['Total_sites'] =gdf[site_facilities_col].sum(axis=1)
    # compute the site  denstity per 10k people
    gdf['health_density'] = np.round((gdf['Total_sites']/gdf['IHSI_UNFPA'])*10000,3)
    # add the display total site the tooltips
    sectiontool.append(("Nombre de sites","@Total_sites"))
    # set the geometry
    gdf.set_geometry('geometry')
    # returns the toolTip and the geodataframe
    return sectiontool,gdf

# global mapping dictianary variable   
map_dict ={'all':'Total des établissements de santé','hosp':'Hopitaux','cal':'Centres de santé avec lits','disp':'Dispensaires','disp+cal':'Dispensaires + Centres de santé avec lits','hosp+cal':'Hopitaux + Centres de santé avec lits','hosp+disp':'Hopitaux + Dispensaires'}
color_map_data = None




# the geodataframe for plotting in bokeh
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


# the geodatasource for plotting in bokeh
def getGeoSource(gdf):
    merged_json=json.loads(gdf.to_json())
    json_data = json.dumps(merged_json)
    return GeoJSONDataSource(geojson = json_data)

# the build map color for dataframe
# Owner Yvel Marcelin
def df_map_color(data,column,palette = 'RdYlBu',range = 10):
    # creates a color palette
    palette = brewer['RdYlBu'][range]
    # reverses the color palette
    palette =palette[::-1]
    # 
    data['color'] = pd.cut(data[column], bins=range,labels=list(palette))
    color_map = data[data.color.notna()].groupby(['color'])[column].min().to_frame().reset_index() 
    color_map = color_map[color_map[column].notna()]
    return color_map,data

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
    p1.patches('xs','ys',source=geosource, line_color = "white", line_width =1, fill_alpha = 0.7,
               fill_color={'field' :column , 'transform': color_mapper},)
    TOOLTIPS = tooltip
    p1.sizing_mode = "stretch_both"
    p1.add_tools(HoverTool(tooltips=TOOLTIPS))
    p1.add_layout(color_bar, 'above')
    return p1







app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.route('/',methods=['GET', 'POST'])
def index():
  # call the filtered dataset for departement table (division,site)
   _,gdf2 = get_filtered_dataset('departement','all')
   # sorts the dataset by Population
   gdf2.sort_values(by =['IHSI_UNFPA'],ascending=False,inplace=True)
   # converts the amount of population  and sites to integer
   gdf2['Total_sites'] = gdf2['Total_sites'].astype('int')
   gdf2['IHSI_UNFPA']=gdf2['IHSI_UNFPA'].astype('int')
   gdf = None
   sectiontool=[]
   # set default values for division an site
   division = 'commune'
   etablissement ='all'
   # verifies if is a post call 
   if request.method == 'POST':
       # divion with dropdown disivion values  form
       division = request.form['division'] 
       # etablissement with dropdown etablissement values form
       etablissement =request.form['etablissement']
    
    # call the filtered dataset for map table (division,site)
   sectiontool,gdf = get_filtered_dataset(division,etablissement)
   # plot the map
   p3=plot_map(gdf = gdf,column="Total_sites",title='Répartition des centres de santé par '+ division,tooltip=sectiontool )
   # get the script and div
   script, div = components(p3)
   # define custom css to the div
   div.replace('class="bk-root"','class="bk-root col-11 col-md-12 col-sm-12" style="height: 100vh')
   # return the index html page
   return render_template("index.html", script=script, div=div,division=division, etablissement =etablissement,gdf2=gdf2)
   
# api route for division and site geoJson
@app.route("/api/v1/<division>/<etablissement>")
def get_geodata (division,etablissement,methods=['GET', 'POST']):
  _,gpd = get_filtered_dataset(division,etablissement)
  _,gpd = df_map_color(gpd, 'Total_sites')
  return gpd.to_json()

# api route for leaflet map
@app.route('/index2',methods=['GET', 'POST'])
def index2():
   _,gdf2 = get_filtered_dataset('departement','all')
   gdf2.sort_values(by =['IHSI_UNFPA'],ascending=False,inplace=True)
   gdf2['Total_sites'] = gdf2['Total_sites'].astype('int')
   gdf2['IHSI_UNFPA']=gdf2['IHSI_UNFPA'].astype('int')
   gdf = None
   sectiontool=[]
   
   division = 'commune'
   etablissement ='all'
   if request.method == 'POST':
       division = request.form['division'] 
       etablissement =request.form['etablissement']
      # fourth
   sectiontools,gdf= get_filtered_dataset(division,etablissement)
   color_map_data,_ = df_map_color(gdf,'Total_sites')
   tool_tips = dict(columns=[],displays=[])
   for tool in sectiontools:
       disp = tool[0]
       col = tool[1].replace('@','')
       tool_tips['columns'].append(col)
       tool_tips['displays'].append(disp)
  
   pal = dict(color=list(color_map_data['color']),values=list(color_map_data['Total_sites']))
   return render_template("index2.html",gdf2 =gdf2,division=division, etablissement =etablissement,tool_tips=tool_tips,palette =pal)


    
if __name__ == '__main__':
	app.run(port=5000, debug=True)

# with your other routes...
