import ast
import numpy as np
import pandas as pd
from pymongo import MongoClient

# Caricamento CSV
df = pd.read_csv("NEWcleaned_moviesDataSet.csv")

print("Colonne CSV rilevate:", df.columns.tolist())

# Trasformazione stringhe in liste 
def parse_list_column(x):
    try:
        # Gestisce sia stringhe formattate come liste sia valori nulli
        if pd.isna(x) or str(x).strip() in ["", "[]", "NaN"]:
            return []
        return [g.strip("'\" ") for g in ast.literal_eval(str(x))]
    except:
        # se ast.literal_eval fallisce su stringhe separate da virgola senza parentesi
        if isinstance(x, str) and x:
            return [g.strip() for g in x.split(",") if g.strip()]
        return []

# Applichiamo la conversione in liste reali a tutte le nuove colonne di tipo array
print("Conversione delle colonne testuali in liste BSON...")
df["genres"] = df["genres_list"].apply(parse_list_column)
df["cast_list_clean"] = df["Cast_list"].apply(parse_list_column)
df["production_companies_list"] = df["production_companies"].apply(parse_list_column)
df["production_countries_list"] = df["production_countries"].apply(parse_list_column)
df["spoken_languages_list"] = df["spoken_languages"].apply(parse_list_column)
df["keywords_list"] = df["keywords"].apply(parse_list_column)

# Pulizia e Ridenominazione colonne

# Rinominiamo le colonne
df = df.rename(columns={
    "id": "_id",                       # Usiamo l'id del film come chiave primaria di Mongo
    "Director": "director",
    "Writer": "writer",
    "Director_of_Photography": "director_of_photography",
    "Producers": "producers",
    "Music_Composer": "music_composer",
    "AverageRating": "average_rating",
    "IMDB_Rating": "imdb_rating",
    "Meta_score": "meta_score"
})

# Raggruppiamo le 4 stelle principali in un unico array "stars" per semplificare le query sul cast
def raggruppa_stars(row):
    stars = []
    for i in range(1, 5):
        val = row[f"Star{i}"]
        if pd.notna(val) and str(val).strip() != "":
            stars.append(str(val).strip())
    return stars

df["stars"] = df.apply(raggruppa_stars, axis=1)

# Rimuoviamo le vecchie colonne non più necessarie per non duplicare i dati 
colonne_da_rimuovere = [
    "genres_list", "Cast_list", "production_companies", 
    "production_countries", "spoken_languages", "keywords",
    "Star1", "Star2", "Star3", "Star4"
]
df = df.drop(columns=[col for col in colonne_da_rimuovere if col in df.columns])

# Rimuovi colonne duplicate residue
df = df.loc[:, ~df.columns.duplicated()]

# Sostituiamo i NaN con None 
df = df.replace({np.nan: None})

# Connessione a MongoDB
client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
db = client["movies_db"]
collection = db["movies"]

# Inserimento dati in batch
batch_size = 10000
records = df.to_dict(orient="records")

print(f"Inizio inserimento di {len(records)} record in MongoDB...")
for i in range(0, len(records), batch_size):
    collection.insert_many(records[i:i+batch_size])
    print(f"Inseriti record {i} - {min(i+batch_size, len(records))}")

# Creazione indici 
print("Verifica e creazione indici...")
existing_indexes = collection.index_information()

if "title_1" not in existing_indexes:
    collection.create_index("title", background=True)

if "genres_1" not in existing_indexes:
    collection.create_index("genres", background=True) # Indice multikey automatico per gli array

if "vote_average_1" not in existing_indexes:
    collection.create_index("vote_average", background=True)

if "imdb_rating_1" not in existing_indexes:
    collection.create_index("imdb_rating", background=True)

print("Import, pulizia e indicizzazione completati correttamente!")
