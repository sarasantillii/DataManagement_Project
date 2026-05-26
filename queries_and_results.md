# SQL vs NoSQL Queries and Performance Analysis

## Dataset Analysis – PostgreSQL vs MongoDB

This document contains the main queries used to compare PostgreSQL and MongoDB using the same movie dataset.

The comparison focuses on:

* query complexity
* execution time
* relational vs document-oriented approaches
* efficiency differences

---

# Query 1 – Complete Movie Retrieval

## Objective

Retrieve all information about a single movie (`Inception`, id = 27205), including:

* genres
* cast
* keywords
* ratings
* director

---

## PostgreSQL Query

```sql
SELECT  
    m.title, 
    l.iso_code AS language, 
    r.imdb_rating, 
    c.director, 
    STRING_AGG(DISTINCT g.name, ', ') AS genres, 
    STRING_AGG(DISTINCT a.name, ', ') AS cast_list, 
    STRING_AGG(DISTINCT w.name, ', ') AS writers, 
    STRING_AGG(DISTINCT k.name, ', ') AS keywords 
FROM movies m 
LEFT JOIN languages l ON m.language_id = l.language_id 
LEFT JOIN movie_ratings r ON m.id = r.movie_id 
LEFT JOIN movie_crew c ON m.id = c.movie_id 
LEFT JOIN movie_genres mg ON m.id = mg.movie_id 
LEFT JOIN genres g ON mg.genre_id = g.genre_id 
LEFT JOIN movie_actors ma ON m.id = ma.movie_id 
LEFT JOIN actors a ON ma.actor_id = a.actor_id 
LEFT JOIN movie_writers mw ON m.id = mw.movie_id 
LEFT JOIN writers w ON mw.writer_id = w.writer_id 
LEFT JOIN movie_keywords mk ON m.id = mk.movie_id 
LEFT JOIN keywords k ON mk.keyword_id = k.keyword_id 
GROUP BY m.id, m.title, l.iso_code, r.imdb_rating, c.director;
```

---

## MongoDB Query

```javascript
db.movies.find(
  { "_id": 27205 },
  {
    "title": 1,
    "release_year": 1,
    "imdb_rating": 1,
    "director": 1,
    "genres": 1,
    "cast_list_clean": 1,
    "keywords_list": 1
  }
)
```

---

## Analysis

### PostgreSQL

* Requires multiple JOIN operations
* Strong relational consistency
* More complex query structure

### MongoDB

* Simpler query
* Faster document retrieval
* Benefits from embedded data

---

# Query 2 – Filtering by Genre, Keyword and Rating

## Objective

Find movies:

* with genre `Sci-Fi` or `Action`
* containing keyword `space`
* IMDb rating greater than 8.0
* ordered by popularity

---

## PostgreSQL Query

```sql
SELECT m.title, m.popularity, r.imdb_rating
FROM movies m
JOIN movie_ratings r ON m.id = r.movie_id
WHERE r.imdb_rating > 8.0
  AND m.id IN (
      SELECT mg.movie_id FROM movie_genres mg
      JOIN genres g ON mg.genre_id = g.genre_id
      WHERE g.name IN ('Sci-Fi', 'Action')
  )
  AND m.id IN (
      SELECT mk.movie_id FROM movie_keywords mk
      JOIN keywords k ON mk.keyword_id = k.keyword_id
      WHERE k.name = 'space'
  )
ORDER BY m.popularity DESC;
```

### Execution Time

`~0.353 seconds`

---

## MongoDB Query

```javascript
db.movies.find({
  "imdb_rating": { $gt: 8.0 },
  "genres": { $in: ["Sci-Fi", "Action"] },
  "keywords_list": "space"
})
.sort({ "popularity": -1 })
.limit(10)
```

### Execution Time

`~0.15 seconds`

---

## Analysis

MongoDB performs better because:

* genres and keywords are embedded arrays
* no JOIN operations are required
* document locality improves filtering performance

PostgreSQL requires:

* subqueries
* joins
* additional filtering stages

---

# Query 3 – Most Frequent Actor Collaborations

## Objective

Find pairs of actors who acted together most frequently.

---

## PostgreSQL Query

```sql
SELECT  
    a1.name AS actor_1,  
    a2.name AS actor_2,  
    COUNT(*) AS movies_together
FROM movie_actors ma1
JOIN movie_actors ma2
    ON ma1.movie_id = ma2.movie_id
    AND ma1.actor_id < ma2.actor_id
JOIN actors a1 ON ma1.actor_id = a1.actor_id
JOIN actors a2 ON ma2.actor_id = a2.actor_id
GROUP BY a1.name, a2.name
HAVING COUNT(*) > 1
ORDER BY movies_together DESC
LIMIT 20;
```

### Execution Time

`~17 minutes`

---

## MongoDB Query

```javascript
pipeline = [

    {
        "$match": {
            "cast_list_clean": {"$exists": True, "$type": "array"},
            "$expr": {"$gte": [{"$size": "$cast_list_clean"}, 2]}
        }
    },

    {
        "$project": {
            "pairs": {
                "$let": {
                    "vars": {
                        "sorted_stars": {
                            "$sortArray": {
                                "input": "$cast_list_clean",
                                "sortBy": 1
                            }
                        }
                    },
                    "in": {
                        "$reduce": {
                            "input": {
                                "$range": [
                                    0,
                                    {"$size": "$$sorted_stars"}
                                ]
                            },
                            "initialValue": [],
                            "in": {
                                "$concatArrays": [
                                    "$$value",
                                    {
                                        "$map": {
                                            "input": {
                                                "$range": [
                                                    {"$add": ["$$this", 1]},
                                                    {"$size": "$$sorted_stars"}
                                                ]
                                            },
                                            "as": "next_idx",
                                            "in": [
                                                {
                                                    "$arrayElemAt": [
                                                        "$$sorted_stars",
                                                        "$$this"
                                                    ]
                                                },
                                                {
                                                    "$arrayElemAt": [
                                                        "$$sorted_stars",
                                                        "$$next_idx"
                                                    ]
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }
    },

    { "$unwind": "$pairs" },

    {
        "$group": {
            "_id": "$pairs",
            "collaborations_count": { "$sum": 1 }
        }
    },

    { "$sort": { "collaborations_count": -1 } },

    { "$limit": 10 },

    {
        "$project": {
            "_id": 0,
            "actor_1": { "$arrayElemAt": ["$_id", 0] },
            "actor_2": { "$arrayElemAt": ["$_id", 1] },
            "collaborations_count": 1
        }
    }

]
```

### Execution Time

`~37 minutes`

---

## Analysis

PostgreSQL performs significantly better for:

* relational analysis
* graph-like relationships
* aggregations involving joins

MongoDB struggles because:

* actor relationships are embedded in arrays
* aggregation pipeline becomes computationally expensive

---

# Query 4 – Full Text Search

## Objective

Search movie overviews containing:

* “space”
* “war”

---

# PostgreSQL

## Index Creation

```sql
CREATE INDEX idx_movies_overview_fts
ON movies
USING gin(to_tsvector('english', overview));
```

### Index Creation Time

`~4 minutes 37 seconds`

---

## Query

```sql
SELECT  
    m.title,
    m.release_year,
    ts_rank(to_tsvector('english', m.overview), query) AS score
FROM movies m,
     to_tsquery('english', 'space & war') query
WHERE to_tsvector('english', m.overview) @@ query
ORDER BY score DESC
LIMIT 10;
```

---

# MongoDB

## Index Creation

```javascript
db.movies.createIndex({ "overview": "text" });
```

---

## Query

```javascript
cursor = collection.find(

    {"$text": {"$search": '\"space\" \"war\"'}},

    {
        "title": 1,
        "release_year": 1,
        "score": {"$meta": "textScore"},
        "_id": 0
    }

).sort([("score", {"$meta": "textScore"})]).limit(10)

results = list(cursor)
```

### Execution Time

`~0.2285 seconds`

---

## Analysis

MongoDB provides:

* easier full-text search configuration
* fast retrieval for text queries

PostgreSQL provides:

* more advanced ranking capabilities
* better configurability
* more control over linguistic analysis

---

# Flexibility Comparison

## Scenario 1 – Schema Evolution

### Add a new field:

`youtube_trailer`

---

## PostgreSQL

```sql
ALTER TABLE movies
ADD COLUMN youtube_trailer TEXT;
```

### Problems

* schema modification required
* possible table locking
* NULL values added to all rows

---

## MongoDB

```javascript
result = collection.update_one(

    { "_id": 27205 },

    {
        "$set": {
            "youtube_trailer":
            "https://www.youtube.com/watch?v=YoHD9XEInc0"
        }
    }
)
```

### Advantages

* no schema migration
* dynamic fields
* immediate update

---

# Scenario 2 – Data Consistency

## Actor Name Update

`Brad Pitt` → `William Brad Pitt`

---

## PostgreSQL

```sql
UPDATE actors
SET name = `William Brad Pitt`
WHERE name = `Brad Pitt`;
```

### Advantages

* update performed once
* normalization guarantees consistency
* no duplicated data

---

## MongoDB

```javascript
result = collection.update_many(

    {"cast_list_clean": "Brad Pitt"},

    {
        "$set": {
            "cast_list_clean.$[elemento]":
            "William Brad Pitt"
        }
    },

    array_filters=[{"elemento": "Brad Pitt"}]
)
```

### Problems

* multiple document updates
* high I/O cost
* denormalized redundancy

---

# Final Conclusions

## PostgreSQL is better for:

* complex relational queries
* analytical workloads
* consistency
* normalized schemas

## MongoDB is better for:

* flexible schemas
* document retrieval
* rapid development
* read-heavy applications

## Main Insight

There is no universally superior DBMS.

The best choice depends on:

* application requirements
* data structure
* scalability needs
* query patterns
