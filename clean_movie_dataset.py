
import pandas as pd
import numpy as np

df = pd.read_csv('moviesDataSet.csv', on_bad_lines='skip', low_memory=False)

# eliminazione colonne non necessarie
newdf = df.drop([
"poster_path","homepage","tagline",
"status","adult","backdrop_path","original_title",
"Poster_Link", "overview_sentiment","Certificate"
], axis='columns')

# eliminazione righe duplicate (basato su id)
newdf = newdf.drop_duplicates(subset=['id'], keep='first')

# eliminazione righe con valori null nelle colonne importanti
newdf = newdf.dropna(subset=["title","release_year","vote_average","genres_list"])

# Anno, revenue e budget --> numeri interi
cols_to_int = ['release_year', 'revenue', 'budget',]
for col in cols_to_int:
    newdf[col] = pd.to_numeric(newdf[col]).astype(int)
    
# Rimozione righe con release_year < 1888 (anno del primo film)
newdf = newdf[newdf['release_year'] >= 1888]

# Annullamento righe con revenue o budget < 1000 (considerati errori di inserimento)
newdf.loc[newdf['revenue'] < 1000, 'revenue'] = np.nan
newdf.loc[newdf['budget'] < 1000, 'budget'] = np.nan

# Salva il file pulito "NEWcleaned_moviesDataSet.csv"
newdf.to_csv("NEWcleaned_moviesDataSet.csv", index=False)
print(newdf.info())

print("Righe iniziali:", len(df))
print("Righe dopo pulizia:", len(newdf))
