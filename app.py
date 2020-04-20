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


def generate_PCODE(depart):
     code = '00'+ str(depart)
     return 'HT'+ code[len(code)-2:]
     
def generate_PCODE2(vilcom):
     code = '00'+ str(vilcom)
     return code[len(code)-2:]
# comma
def add_comma(data):
    val= ''
    index =0
    for v in data[::-1]:
       if index%3 == 0 and index !=0 :
            val=val+','
       val+=v
       index+=1
    return val[::-1]

def load_com(spa=None,dept=None,boudaries_dep=None,pop_dep=None):

    # STEP 1
    # loads spa dataset
    spa = pd.read_csv('spa.csv')
    # replaces blank space by (_)
    spa['facdesc_1'] = spa['facdesc_1'].str.replace(' ','_')
    # computes dummies columns
    spa = pd.get_dummies(spa, columns=['facdesc_1'],prefix='',prefix_sep='')
    # sums the site health facilities
    com  = spa.groupby(['depart','departn','vilcomn','vilcom'])['CENTRE_DE_SANTE_AVEC_LIT','DISPENSAIRE','HOPITAL','CENTRE_DE_SANTE_SANS_LIT'].sum().reset_index()
    # renames columns needed
    com= com.rename(columns={'departn':'ADM1_FR','vilcomn':'ADM2_FR'})
    # generats PCODE
    com['ADM2_PCODE'] = com['depart'].apply(lambda x: generate_PCODE(x))+ com['vilcom'].apply(lambda x: generate_PCODE2(x))
    # remove duplicates
    com =com.groupby(['ADM2_PCODE'])['CENTRE_DE_SANTE_AVEC_LIT','DISPENSAIRE','HOPITAL','CENTRE_DE_SANTE_SANS_LIT'].sum().reset_index()

    # STEP 2
    # reads adm2 shapefiles
    boudaries_com = gpd.read_file('boundaries/hti_admbnda_adm2_cnigs_20181129.shp')
    # sets the geometry column
    boudaries_com.set_geometry('geometry')
    # selects features needed
    boudaries_com = boudaries_com[['ADM2_PCODE','ADM1_EN','ADM1_FR','ADM2_EN','ADM2_FR','geometry']]

    
    # STEP 3
    # reads population dataset
    pop_com = pd.read_excel('datasets/hti_adminboundaries_tabulardata.xlsx',sheet_name='hti_pop2019_adm2')
    # selects feautures needed
    pop_com = pop_com[['adm2code','IHSI_UNFPA_2019','IHSI_UNFPA_2019_female','IHSI_UNFPA_2019_male']]
    # renames adm1code to ADM1_PCODE
    pop_com = pop_com.rename(columns ={"adm2code": "ADM2_PCODE"})




     # STEP 4
    boudaries_com =pd.merge(boudaries_com,com,how ='left',left_on=['ADM2_PCODE'],right_on= ['ADM2_PCODE'])
    boudaries_com = pd.merge(boudaries_com,pop_com,how ='left',on=['ADM2_PCODE'])
    boudaries_com.sort_values(by ='ADM2_PCODE')    

    return boudaries_com
     
def load_depart(spa=None,dept=None,boudaries_dep=None,pop_dep=None):

    # STEP 1
    # loads spa dataset
    spa = pd.read_csv('spa.csv')
    # replaces blank space by (_)
    spa['facdesc_1'] = spa['facdesc_1'].str.replace(' ','_')
    # computes dummies columns
    spa = pd.get_dummies(spa, columns=['facdesc_1'],prefix='',prefix_sep='')
    # sums the site health facilities
    dept = spa.groupby(['departn','depart'])['CENTRE_DE_SANTE_AVEC_LIT','DISPENSAIRE','HOPITAL','CENTRE_DE_SANTE_SANS_LIT'].sum()
    # renames departn column to ADM1_FR perform merging
    dept=dept.reset_index().rename(columns= {'departn':'ADM1_FR'})
    # generates PCODE
    dept['ADM1_PCODE'] = dept['depart'].apply(lambda x: generate_PCODE(x))

    # STEP 2
    # reads adm1 shapefiles
    boudaries_dep = gpd.read_file('boundaries/hti_admbnda_adm1_cnigs_20181129.shp')
    # sets the geometry column
    boudaries_dep.set_geometry('geometry')
    # selects features needed
    boudaries_dep=boudaries_dep[['ADM1_EN','ADM1_FR','ADM1_HT','ADM1_PCODE','geometry']]

    
    # STEP 3
    # reads population dataset
    pop_dep = pd.read_excel('datasets/hti_adminboundaries_tabulardata.xlsx',sheet_name='hti_pop2019_adm1')
    # selects feautures needed
    pop_dep = pop_dep[['adm1code','IHSI_UNFPA_2019','IHSI_UNFPA_2019_female','IHSI_UNFPA_2019_male']]
    # renames adm1code to ADM1_PCODE
    pop_dep =pop_dep.rename(columns ={"adm1code": "ADM1_PCODE"})

     # STEP 4
    boudaries_dep = pd.merge(boudaries_dep,dept,how ='left',left_on=['ADM1_PCODE'],right_on= ['ADM1_PCODE'])
    # renames column 
    boudaries_dep = boudaries_dep.rename(columns ={'ADM1_FR_x': 'ADM1_FR'})
    # selects features
    columns = ['ADM1_PCODE','ADM1_EN','ADM1_FR','ADM1_HT','geometry','CENTRE_DE_SANTE_AVEC_LIT','DISPENSAIRE','HOPITAL','CENTRE_DE_SANTE_SANS_LIT']
    boudaries_dep = boudaries_dep[columns]
    # merges all dataset
    boudaries_dep = pd.merge(boudaries_dep,pop_dep,how ='left',on='ADM1_PCODE')
    return boudaries_dep

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
        gdf = load_com()
        sectiontool.append( ("Depatman","@ADM1_FR"))
        sectiontool.append(("Komin","@ADM2_FR"))
    elif filter == 'departement':
        gdf =load_depart()
        sectiontool.append( ("Departement","@ADM1_FR"))
    

   

    # selects health site facililites
    if col == 'all':
        site_facilities_col = ['CENTRE_DE_SANTE_AVEC_LIT','DISPENSAIRE','HOPITAL','CENTRE_DE_SANTE_SANS_LIT']
        sectiontool.append(("Dispanse:","@DISPENSAIRE"))
        sectiontool.append( ("Lopital:","@HOPITAL"))
        sectiontool.append( ("Sant sante avek kabann:","@CENTRE_DE_SANTE_AVEC_LIT"))
        sectiontool.append( ("Sant sante san kabann:","@CENTRE_DE_SANTE_SANS_LIT"))
    elif col == 'hosp':
        site_facilities_col = ['HOPITAL']
        sectiontool.append( ("Lopital","@HOPITAL"))
       
    elif col == 'cal':
        site_facilities_col = ['CENTRE_DE_SANTE_AVEC_LIT']
        sectiontool.append( ("Sant sante avek kabann:","@CENTRE_DE_SANTE_AVEC_LIT"))
    elif col == 'disp':
        site_facilities_col = ['DISPENSAIRE']
        sectiontool.append(("Dispansé:","@DISPENSAIRE"))
    elif col == 'csl':
        site_facilities_col = ['CENTRE_DE_SANTE_SANS_LIT']
        sectiontool.append(("Sant sante san kabann::","@CENTRE_DE_SANTE_SANS_LIT"))


    
    # selects non site facilities columns

    admin_cols = [col for col in gdf.columns if col not in site_facilities_col]
     # selects columns needed to display on the map
    gdf = gdf[admin_cols+site_facilities_col]
    gdf.rename(columns={'IHSI_UNFPA_2019':'IHSI_UNFPA'},inplace =True)
    # fill na values by 0.0
    gdf[site_facilities_col] = gdf[site_facilities_col].fillna(0.0)
    # sum the total health site facilities
    gdf['Total_sites'] =gdf[site_facilities_col].sum(axis=1)
    # compute the site  denstity per 10k people
    gdf['health_density'] = np.round((gdf['Total_sites']/gdf['IHSI_UNFPA'])*10000,3)
    # add the display total site the tooltips
    sectiontool.append(("Kantite sant sante","@Total_sites"))
    # set the geometry
    gdf.set_geometry('geometry')
    # returns the toolTip and the geodataframe
    return sectiontool,gdf

# global mapping dictianary variable   
map_dict ={'all':'Tout sant sante yo','hosp':'Lopital','cal':'Sant sante avek kabann:','disp':'Dispanse','commune':'komin','departement':'depatman'}
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
    # add the color column to dataframe
    data['color'] = pd.cut(data[column], bins=range,labels=list(palette))
    # computes the palette legend
    color_map = data[data.color.notna()].groupby(['color'])[column].min().to_frame().reset_index() 
    # removes non display colunms
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















@app.route('/')
def home():
    return render_template('home.html')


@app.route('/index',methods=['GET', 'POST'])
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
   p3=plot_map(gdf = gdf,column="Total_sites",title='Distribisyon sant sante yo pa '+ division,tooltip=sectiontool )
   # get the script and div
   script, div = components(p3)
   # define custom css to the div
   div.replace('class="bk-root"','class="bk-root col-11 col-md-12 col-sm-12" style="height: 100vh')
   # return the index html page
   return render_template("index.html", script=script, div=div,division=division, etablissement =etablissement,gdf2=gdf2 ,title=map_dict[division])
   
# api route for division and site geoJson
@app.route("/api/v1/<division>/<etablissement>")
def get_geodata (division,etablissement,methods=['GET', 'POST']):
  _,gpd = get_filtered_dataset(division,etablissement)
  _,gpd = df_map_color(gpd, 'Total_sites')
  return gpd.to_json()

# api route for leaflet map
@app.route('/index2',methods=['GET', 'POST'])
def index2():
    # call the filtered dataset for departement table (division,site)
   _,gdf2 = get_filtered_dataset('departement','all')

   gdf2.sort_values(by =['IHSI_UNFPA'],ascending=False,inplace=True)
   gdf2['Total_sites'] = gdf2['Total_sites'].astype('int')
   gdf2['IHSI_UNFPA']=gdf2['IHSI_UNFPA'].astype('int')
   gdf2['IHSI_UNFPA']=gdf2['IHSI_UNFPA'].astype('str')
   gdf2['IHSI_UNFPA'] =  gdf2['IHSI_UNFPA'].apply(lambda x: add_comma(x))
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

   palette = brewer['RdYlBu'][10]
   palette = palette[::-1]
   color_mapper = LinearColorMapper(palette = palette, low = gdf['Total_sites'].min(), high = gdf['Total_sites'].max())
   color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8, width=500, height=20, 
                         location=(0,0), orientation='horizontal')
  
  
   pal = dict(color=list(color_map_data['color']),values=list(color_map_data['Total_sites']))
   return render_template("index2.html",gdf2 =gdf2,division=division, etablissement =etablissement,tool_tips=tool_tips,palette =pal,title =map_dict[division])

def get_all_dept():
   mspp_covid19_cases = pd.read_csv('datasets/mspp_covid19_cases.csv')
   my_list = []
   for _,row in mspp_covid19_cases.iterrows():
    my_list.append(dict(departement	= row['departement'],cas_confirmes=row['cas_confirmes'],deces = row['deces'],taux_de_letalite = row['taux_de_letalite'],document_date =row['document_date']))
   my_list
   return my_list

# api route for division and site geoJson
@app.route("/api/v1/covid19ht/departement/<departement>")
def get_covid19ht (departement = '',methods=['GET', 'POST']):
   my_list = []
   mspp_covid19_cases = pd.read_csv('datasets/mspp_covid19_cases.csv')
   if departement == 'all':
       for _,row in mspp_covid19_cases.iterrows():
            my_list.append(dict(departement	= row['departement'],cas_confirmes=row['cas_confirmes'],deces = row['deces'],taux_de_letalite = row['taux_de_letalite'],document_date =row['document_date']))
   else:
       mspp_covid19_cases = mspp_covid19_cases[mspp_covid19_cases['departement'] == departement ]
       for _,row in mspp_covid19_cases.iterrows():
            my_list.append(dict(departement	= row['departement'],cas_confirmes=row['cas_confirmes'],deces = row['deces'],taux_de_letalite = row['taux_de_letalite'],document_date =row['document_date']))

   return jsonify(my_list)

@app.route("/api/v1/covid19ht/date/<date>")
def get_covid19ht2 (date = 'all',methods=['GET', 'POST']):
   my_list = []
   mspp_covid19_cases = pd.read_csv('datasets/mspp_covid19_cases.csv')
   if date == 'all':
       for _,row in mspp_covid19_cases.iterrows():
            my_list.append(dict(departement	= row['departement'],cas_confirmes=row['cas_confirmes'],deces = row['deces'],taux_de_letalite = row['taux_de_letalite'],document_date =row['document_date']))
   else:
       mspp_covid19_cases = mspp_covid19_cases[mspp_covid19_cases['document_date'] == date ]
       for _,row in mspp_covid19_cases.iterrows():
            my_list.append(dict(departement	= row['departement'],cas_confirmes=row['cas_confirmes'],deces = row['deces'],taux_de_letalite = row['taux_de_letalite'],document_date =row['document_date']))

   return jsonify(my_list)

@app.route("/api/v1/covid19ht/")
def get_covid19ht3 (methods=['GET', 'POST']):
   my_list = []
   mspp_covid19_cases = pd.read_csv('datasets/mspp_covid19_cases.csv')
  
   for _,row in mspp_covid19_cases.iterrows():
      my_list.append(dict(departement	= row['departement'],cas_confirmes=row['cas_confirmes'],deces = row['deces'],taux_de_letalite = row['taux_de_letalite'],document_date =row['document_date']))
   return jsonify(my_list)
    

    
if __name__ == '__main__':
	app.run(port=5000, debug=True)

# with your other routes...
