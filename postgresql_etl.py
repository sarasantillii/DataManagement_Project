import pandas as pd
import numpy as np
import psycopg2
from psycopg2 import extras
import ast

# Caricamento del dataset
df = pd.read_csv('NEWcleaned_moviesDataSet.csv')

# Uniformiamo i nomi delle colonne per evitare problemi di case-sensitivity in Python/Pandas
# Mappiamo i nomi reali del dataframe a quelli attesi
df = df.rename(columns={
    'Director': 'director',
    'Writer': 'writer',
    'Director_of_Photography': 'dop',
    'Producers': 'producers',
    'Music_Composer': 'music_composer',
    'AverageRating': 'average_rating',
    'IMDB_Rating': 'imdb_rating'
})

# Sostituzione di NaN con None (vengono letti come NULL da PostgreSQL)
df = df.where(pd.notnull(df), None)
df['release_date'] = pd.to_datetime(df['release_date']).dt.date

# Connessione a PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    database="moviesDB",  
    user="user1",
    password="password",
    port="5432"
)
cur = conn.cursor()

# Funzione helper per estrarre elementi da stringhe simil-lista o testuali
def parse_list_column(val):
    if not val:
        return []
    try:
        # Se è formattato come lista python ['A', 'B']
        parsed = ast.literal_eval(str(val))
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        return [str(parsed).strip()]
    except:
        # Se è una stringa separata da virgole o sporca
        cleaned = str(val).replace('[', '').replace(']', '').replace("'", "").replace('"', '')
        return [item.strip() for item in cleaned.split(',') if item.strip()]

try:
    print("Rimozione tabelle esistenti...")
    # DROPPING TABLES (ordine inverso per via dei vincoli FK)
    tables_to_drop = [
        "movie_genres", "movie_actors", "movie_writers", 
        "movie_keywords", "movie_crew", "movie_ratings",
        "genres", "actors", "writers", "keywords", "languages", "movies"
    ]
    for table in tables_to_drop:
        cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")

    print("Creazione nuove tabelle...")
    
    # 1. Tabella delle Lingue
    cur.execute("""
        CREATE TABLE languages (
            language_id SERIAL PRIMARY KEY,
            iso_code VARCHAR(10) UNIQUE NOT NULL
        );
    """)

    # 2. Tabella Principale Movies
    cur.execute("""
        CREATE TABLE movies (
            id INT PRIMARY KEY,
            title TEXT NOT NULL,
            vote_average NUMERIC,
            vote_count INT,
            release_date DATE,
            release_year INT,
            revenue NUMERIC,
            budget NUMERIC,
            runtime INT,
            popularity NUMERIC,
            overview TEXT,
            imdb_id TEXT,
            language_id INT REFERENCES languages(language_id)
        );
    """)

    # 3. Tabelle Anagrafiche Esterne
    cur.execute("CREATE TABLE genres (genre_id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL);")
    cur.execute("CREATE TABLE actors (actor_id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL);")
    cur.execute("CREATE TABLE writers (writer_id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL);")
    cur.execute("CREATE TABLE keywords (keyword_id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL);")

    # 4. Tabelle di Relazione N:M e Tabelle Satellite
    cur.execute("""
        CREATE TABLE movie_genres (
            movie_id INT REFERENCES movies(id) ON DELETE CASCADE,
            genre_id INT REFERENCES genres(genre_id) ON DELETE CASCADE,
            PRIMARY KEY (movie_id, genre_id)
        );
    """)

    cur.execute("""
        CREATE TABLE movie_actors (
            movie_id INT REFERENCES movies(id) ON DELETE CASCADE,
            actor_id INT REFERENCES actors(actor_id) ON DELETE CASCADE,
            PRIMARY KEY (movie_id, actor_id)
        );
    """)

    cur.execute("""
        CREATE TABLE movie_writers (
            movie_id INT REFERENCES movies(id) ON DELETE CASCADE,
            writer_id INT REFERENCES writers(writer_id) ON DELETE CASCADE,
            PRIMARY KEY (movie_id, writer_id)
        );
    """)

    cur.execute("""
        CREATE TABLE movie_keywords (
            movie_id INT REFERENCES movies(id) ON DELETE CASCADE,
            keyword_id INT REFERENCES keywords(keyword_id) ON DELETE CASCADE,
            PRIMARY KEY (movie_id, keyword_id)
        );
    """)

    cur.execute("""
        CREATE TABLE movie_crew (
            movie_id INT PRIMARY KEY REFERENCES movies(id) ON DELETE CASCADE,
            director TEXT,
            dop TEXT,
            composer TEXT,
            producers TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE movie_ratings (
            movie_id INT PRIMARY KEY REFERENCES movies(id) ON DELETE CASCADE,
            imdb_rating NUMERIC,
            average_rating NUMERIC
        );
    """)

    print("Tabelle create. Inizio elaborazione e popolamento...")

    # --- POPOLAMENTO DIZIONARI DI LOOKUP (Lingue, Generi, Attori, Scrittori, Keywords) ---
    print("Estrazione valori unici per anagrafiche...")
    
    unique_languages = set(df['original_language'].dropna())
    unique_genres = set()
    unique_actors = set()
    unique_writers = set()
    unique_keywords = set()

    for idx, row in df.iterrows():
        unique_genres.update(parse_list_column(row['genres_list']))
        unique_actors.update(parse_list_column(row['Cast_list']))
        unique_writers.update(parse_list_column(row['writer']))
        # Uniamo keywords e all_combined_keywords per sicurezza, prendendo la colonna principale
        unique_keywords.update(parse_list_column(row['keywords']))

    # Funzione per inserire entità uniche e mappare i loro ID in un dizionario Python
    def populate_lookup_table(table_name, column_name, id_column, items_set):
        mapping = {}
        print(f"Inserimento di {len(items_set)} elementi in {table_name}...")
        for item in items_set:
            cur.execute(f"INSERT INTO {table_name} ({column_name}) VALUES (%s) ON CONFLICT ({column_name}) DO NOTHING RETURNING {id_column};", (item,))
            res = cur.fetchone()
            if res:
                mapping[item] = res[0]
            else:
                cur.execute(f"SELECT {id_column} FROM {table_name} WHERE {column_name}=%s;", (item,))
                mapping[item] = cur.fetchone()[0]
        return mapping

    lang_map = populate_lookup_table("languages", "iso_code", "language_id", unique_languages)
    genre_map = populate_lookup_table("genres", "name", "genre_id", unique_genres)
    actor_map = populate_lookup_table("actors", "name", "actor_id", unique_actors)
    writer_map = populate_lookup_table("writers", "name", "writer_id", unique_writers)
    keyword_map = populate_lookup_table("keywords", "name", "keyword_id", unique_keywords)

    # --- INSERIMENTO TABELLA MOVIES ---
    print("Preparazione e inserimento dei Film...")
    movies_data = []
    for idx, row in df.iterrows():
        lang_id = lang_map.get(row['original_language']) if row['original_language'] else None
        movies_data.append((
            row['id'], row['title'], row['vote_average'], row['vote_count'],
            row['release_date'], row['release_year'], row['revenue'], row['budget'],
            row['runtime'], row['popularity'], row['overview'], row['imdb_id'], lang_id
        ))

    query_movies = """
        INSERT INTO movies (id, title, vote_average, vote_count, release_date, release_year, revenue, budget, runtime, popularity, overview, imdb_id, language_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING;
    """
    extras.execute_batch(cur, query_movies, movies_data)

    # --- PREPARAZIONE E INSERIMENTO DELLE RELAZIONI N:M E SATELLITI ---
    print("Elaborazione relazioni e tabelle satelliti...")
    movie_genres_batch = set()
    movie_actors_batch = set()
    movie_writers_batch = set()
    movie_keywords_batch = set()
    
    movie_crew_batch = []
    movie_ratings_batch = []

    for idx, row in df.iterrows():
        m_id = row['id']
        
        # Generi
        for g in parse_list_column(row['genres_list']):
            if g in genre_map: movie_genres_batch.add((m_id, genre_map[g]))
        
        # Attori
        for a in parse_list_column(row['Cast_list']):
            if a in actor_map: movie_actors_batch.add((m_id, actor_map[a]))
            
        # Scrittori
        for w in parse_list_column(row['writer']):
            if w in writer_map: movie_writers_batch.add((m_id, writer_map[w]))
            
        # Keywords
        for k in parse_list_column(row['keywords']):
            if k in keyword_map: movie_keywords_batch.add((m_id, keyword_map[k]))

        # Crew (Trattati come attributi testuali o liste denormalizzate interne alla tabella satellite, come da schema)
        movie_crew_batch.append((
            m_id, 
            row['director'], 
            row['dop'], 
            row['music_composer'], 
            row['producers']
        ))
        
        # Ratings
        movie_ratings_batch.append((
            m_id, 
            row['imdb_rating'], 
            row['average_rating']
        ))

    # Esecuzione dei batch per le tabelle di giunzione
    print("Inserimento relazioni N:M...")
    extras.execute_batch(cur, "INSERT INTO movie_genres (movie_id, genre_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", list(movie_genres_batch))
    extras.execute_batch(cur, "INSERT INTO movie_actors (movie_id, actor_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", list(movie_actors_batch))
    extras.execute_batch(cur, "INSERT INTO movie_writers (movie_id, writer_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", list(movie_writers_batch))
    extras.execute_batch(cur, "INSERT INTO movie_keywords (movie_id, keyword_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", list(movie_keywords_batch))

    # Esecuzione dei batch per le tabelle 1:1 / Satelliti
    print("Inserimento dati Crew e Ratings...")
    extras.execute_batch(cur, "INSERT INTO movie_crew (movie_id, director, dop, composer, producers) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;", movie_crew_batch)
    extras.execute_batch(cur, "INSERT INTO movie_ratings (movie_id, imdb_rating, average_rating) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;", movie_ratings_batch)

    # Commit finale
    conn.commit()
    print("\nDatabase Postgres popolato con successo in modo strutturato e relazionale!")

except Exception as e:
    print(f"\nSi è verificato un errore critico: {e}")
    conn.rollback()
finally:
    cur.close()
    conn.close()
