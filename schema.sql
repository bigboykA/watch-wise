-- WatchWise Database Schema
-- CSC 310 Database Project – Kofi & Mutawakil

-- Directors table
CREATE TABLE IF NOT EXISTS Directors (
    director_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    birth_year  INTEGER,
    nationality TEXT
);

-- Movies table (Many-to-One with Directors)
CREATE TABLE IF NOT EXISTS Movies (
    movie_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    release_year INTEGER NOT NULL,
    genre       TEXT NOT NULL,
    runtime     INTEGER,
    rating      REAL DEFAULT 0,
    description TEXT,
    director_id INTEGER,
    FOREIGN KEY (director_id) REFERENCES Directors(director_id),
    CHECK (rating >= 0 AND rating <= 10),
    UNIQUE (title, release_year)
);

-- Actors table
CREATE TABLE IF NOT EXISTS Actors (
    actor_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    birth_year INTEGER,
    nationality TEXT
);

-- MovieActors junction table (Many-to-Many between Movies and Actors)
CREATE TABLE IF NOT EXISTS MovieActors (
    movie_id INTEGER NOT NULL,
    actor_id INTEGER NOT NULL,
    PRIMARY KEY (movie_id, actor_id),
    FOREIGN KEY (movie_id) REFERENCES Movies(movie_id),
    FOREIGN KEY (actor_id) REFERENCES Actors(actor_id)
);

-- Ratings table (Many-to-One with Movies)
CREATE TABLE IF NOT EXISTS Ratings (
    rating_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id   INTEGER NOT NULL,
    username   TEXT NOT NULL,
    score      REAL NOT NULL,
    review     TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (movie_id) REFERENCES Movies(movie_id),
    CHECK (score >= 0 AND score <= 10)
);
