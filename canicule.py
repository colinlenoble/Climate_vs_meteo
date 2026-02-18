"""
Caractérisation des nombres de jours de canicule : étude

@author: amounier
"""

import time 
import os 
import pandas as pd
import matplotlib.pyplot as plt

def get_open_meteo_url(longitude, latitude, year_start, year_end, daily_variables):
    """
    Récupération de l'url de l'API Open-Météo

    Parameters
    ----------
    longitude : float
        DESCRIPTION.
    latitude : float
        DESCRIPTION.
    year : int
        DESCRIPTION.
    hourly_variables : list of str or str
        DESCRIPTION.

    Returns
    -------
    url : str
        DESCRIPTION.

    """
    if isinstance(daily_variables, list):
        daily_variables = ','.join(daily_variables)
    tod = pd.Timestamp(date.today())
    
    # Si l'année demandée n'est pas terminée, il faut modifier les périodes requêtées
    end_month, end_day = 12, 31
    if year_end == tod.year:
        end_day = tod.strftime('%d')
        end_month = tod.strftime('%m')
        
    url = 'https://archive-api.open-meteo.com/v1/archive?latitude={}&longitude={}&start_date={}-01-01&end_date={}-{}-{}&daily={}&timezone=Europe%2FBerlin'.format(latitude,longitude,year_start,year_end,end_month,end_day,daily_variables)
    # print(url)
    return url


def open_meteo_historical_data(longitude, latitude, year_start, year_end, daily_variables=["snowfall_sum", "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean"], force=False, save = False):
    """
    Ouverture des fichiers meteo

    Parameters
    ----------
    longitude : float
        DESCRIPTION.
    latitude : float
        DESCRIPTION.
    year : int
        DESCRIPTION.
    hourly_variables : str or list of str, optional
        DESCRIPTION. The default is ['temperature_2m','direct_radiation_instant'].
    force : boolean, optional
        DESCRIPTION. The default is False.

    Returns
    -------
    data : pandas DataFrame
        DESCRIPTION.

    """
    if isinstance(daily_variables, list):
        daily_variables_str = ','.join(daily_variables)
    else:
        daily_variables_str = daily_variables
        
    save_path = os.path.join('data','Open-Meteo')
    save_name = '{}_{}_{}_{}.csv'.format(daily_variables_str, year_start, year_end, longitude, latitude)
    save_name_units = '{}_{}_{}_{}_units.txt'.format(daily_variables_str, year_start, year_end, longitude, latitude)

    if save_name not in os.listdir(save_path) or force:
        url = get_open_meteo_url(longitude, latitude, year_start, year_end, daily_variables)
        response = requests.get(url)
        print("Requesting data from Open-Meteo API...")
        import time
        time.sleep(100)  # To avoid hitting rate limits
        json_data = response.json()
        if response.status_code==429:
            print("Too many requests. Waiting before retrying...")
            return None
        data = pd.DataFrame().from_dict(json_data.get('daily'))
        data.to_csv(os.path.join(save_path,save_name), index=False)
        
    data = pd.read_csv(os.path.join(save_path,save_name))
    data = data.set_index('time')
    data.index = pd.to_datetime(data.index)
    return data


# liste des préfectures
pref = pd.read_csv("data/pref_lat_lon.csv", sep=";")
pref["lat"] = pref["Geo Point"].apply(lambda x: float(x.split(",")[0]))
pref["lon"] = pref["Geo Point"].apply(lambda x: float(x.split(",")[1]))
pref = pref[['Code INSEE', 'Commune', 'Service', 'lat', 'lon']]

# seuils de canicules MF
seuils_df = pd.read_csv("data/seuils_canicules.csv", sep=",").set_index('dep')

# coordonnées villes
lons = pref[pref.Service != 'Sous-préfecture'].lon.to_list()
lats = pref[pref.Service != 'Sous-préfecture'].lat.to_list()
communes = pref[pref.Service != 'Sous-préfecture'].Commune.to_list()
pref['Code INSEE'] = pref['Code INSEE'].astype(str).str.zfill(5)
code_insee = pref[pref.Service != 'Sous-préfecture']['Code INSEE'].to_list()

# période d'étude
year_start, year_end = 1950, 2025

# -------------------------------------
def main():
    tic = time.time()

    i_test = communes.index('Nice')
    lon, lat, name, code = lons[i_test], lats[i_test], communes[i_test], code_insee[i_test]
    print(f'{name} ({code})')

    smin,smax = seuils_df.loc[str(int(code[:2]))]
    print(smin,smax)

    dept = code[:2]
    data = open_meteo_historical_data(lon, lat, year_start, year_end, daily_variables=["snowfall_sum", "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean"], force=False, save=False)
    data['canicule'] = data.temperature_2m_mean > (smin+smax)/2

    data = data.resample('YS').agg({'canicule':'sum', 
                                    'temperature_2m_mean':'mean',
                                    'snowfall_sum':'sum'})
                                    # 'nb_days_snow':'sum',
                                    # 'Commune':'first',
                                    # 'Departement':'first'})

    fig,ax = plt.subplots(dpi=300)
    # data.temperature_2m_mean.plot(ax=ax)
    data.canicule.plot(ax=ax)
    xlims=ax.get_xlim()
    # ax.plot(xlims,[(smin+smax)/2]*2)
    plt.show()
    
    tac = time.time()
    print('Done in {:.2f}s.'.format(tac-tic))
    
if __name__ == '__main__':
    main()