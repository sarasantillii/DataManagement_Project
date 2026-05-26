# DataManagement_Project
Comparative analysis of a Relational DBMS (PostgreSQL) and a NoSQL Document Database (MongoDB) using the same movie dataset.

## Project Overview

This project was developed for the **Data Management 2024/2025** course.

The goal of the project is to compare a **Relational DBMS (PostgreSQL)** and a **NoSQL Document Database (MongoDB)** using the same movie dataset and the same analytical queries.

The project follows the academic track:

> *“Select a dataset, a NoSQL tool and a relational DBMS, and compare the results of analyses on different systems, highlighting advantages and disadvantages of each approach in terms of efficiency.”*

The comparison focuses on:

* query complexity
* execution efficiency
* schema flexibility
* data consistency
* scalability
* relational vs document-oriented modeling

---

# Dataset

The project uses the movie dataset "the "IMDb and TMDb Movie Metadata Big Dataset" containing many information about over 1 million of movies & TV shows, available con Kaggle:

https://www.kaggle.com/datasets/shubhamchandra235/imdb-and-tmdb-movie-metadata-big-dataset-1m/data

---

# Technologies Used

## PostgreSQL

Relational database management system used for:

* normalized schema design
* relational analysis
* JOIN-heavy queries
* strong consistency

## MongoDB

Document-oriented NoSQL database used for:

* flexible document storage
* embedded arrays
* fast document retrieval
* aggregation pipelines

## Python Libraries

* pandas
* psycopg2
* pymongo
* numpy

---

# Project Structure

## Data Cleaning

`clean_movie_dataset.py`

* removes duplicates
* handles null values
* converts data types
* validates movie records

## PostgreSQL ETL

`postgresql_etl.py`

* creates relational schema
* populates tables
* manages relationships and foreign keys

## MongoDB ETL

`mongodb_etl.py`

* transforms records into BSON documents
* embeds arrays and nested fields
* creates indexes

---

# Database Design

## PostgreSQL

The relational model follows normalization principles:

* separate tables for entities
* bridge tables for many-to-many relationships
* foreign key constraints

Tables:

* movies
* genres
* actors
* writers
* keywords
* languages
* movie_genres
* movie_actors
* movie_crew
* movie_keywords
* movie_writers
* movie_ratings

## MongoDB

MongoDB stores movie data as documents with embedded arrays:

* genres
* cast
* keywords
* ratings

This reduces JOIN operations and improves read performance.

---

# Main Analyses

The project compares PostgreSQL and MongoDB using:

1. Single movie retrieval
2. Multi-condition filtering
3. Actor collaboration analysis
4. Full-text search
5. Schema flexibility comparison

Execution times and query details are available in:
`queries_and_results.md`

---

# Main Findings

## PostgreSQL Advantages

* excellent for relational analysis
* strong consistency
* efficient complex JOINs
* reduced redundancy

## MongoDB Advantages

* flexible schema
* faster document retrieval
* easier schema evolution
* efficient array filtering

## Final Conclusion

There is no universally better database system.

* PostgreSQL is more suitable for highly relational and analytical workloads.
* MongoDB is more suitable for flexible, read-heavy, and document-oriented applications.

The best choice depends on the application requirements and data structure.

---

# Authors
Sara Santilli 2203141

Martina Stivala 2192706

Data Management Project – Sapienza University of Rome, 2024/2025
