"""
Initialize the WatchWise SQLite database.
Creates tables from schema.sql and inserts sample data.
Run this once before starting the Flask app:
    python init_db.py
"""

import sqlite3

DATABASE = "watchwise.db"


def init():
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON")

    # Create tables from schema file
    with open("schema.sql") as f:
        conn.executescript(f.read())

    # --- Sample Directors ---
    directors = [
        ("Christopher Nolan", 1970, "British-American"),
        ("Bong Joon-ho", 1969, "South Korean"),
        ("Frank Darabont", 1959, "Hungarian-American"),
        ("Greg Mottola", 1964, "American"),
        ("Jordan Peele", 1979, "American"),
        ("Nick Cassavetes", 1959, "American"),
        ("Ava DuVernay", 1972, "American"),
        ("Chad Stahelski", 1968, "American"),
        ("Ari Aster", 1986, "American"),
        ("Damien Chazelle", 1985, "American"),
        ("Wes Anderson", 1969, "American"),
        ("Barry Jenkins", 1979, "American"),
        ("Denis Villeneuve", 1967, "Canadian"),
        ("George Miller", 1945, "Australian"),
        ("John Krasinski", 1979, "American"),
        ("David Fincher", 1962, "American"),
        ("Rian Johnson", 1973, "American"),
        ("Martin Scorsese", 1942, "American"),
        ("Greta Gerwig", 1983, "American"),
        ("Spike Lee", 1957, "American"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO Directors (name, birth_year, nationality) VALUES (?, ?, ?)",
        directors,
    )

    # --- Sample Movies ---
    movies = [
        ("Inception", 2010, "Sci-Fi", 148, 8.8, "A thief who steals corporate secrets through dream-sharing technology is given the task of planting an idea into the mind of a C.E.O.", 1),
        ("The Dark Knight", 2008, "Action", 152, 9.0, "Batman raises the stakes in his war on crime, facing the Joker, a criminal mastermind who brings Gotham to its knees.", 1),
        ("Interstellar", 2014, "Sci-Fi", 169, 8.7, "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.", 1),
        ("Parasite", 2019, "Thriller", 132, 8.5, "Greed and class discrimination threaten the newly formed symbiotic relationship between the wealthy Park family and the destitute Kim clan.", 2),
        ("The Shawshank Redemption", 1994, "Drama", 142, 9.3, "Two imprisoned men bond over a number of years, finding solace and eventual redemption through acts of common decency.", 3),
        ("Superbad", 2007, "Comedy", 113, 7.6, "Two co-dependent high school seniors set out to score alcohol for a party, hoping to finally hook up with the girls they like.", 4),
        ("Get Out", 2017, "Horror", 104, 7.7, "A young African-American visits his white girlfriend's parents for the weekend, where his simmering uneasiness about their reception of him turns into horror.", 5),
        ("The Notebook", 2004, "Romance", 123, 7.8, "A poor yet passionate young man falls in love with a rich young woman, giving her a sense of freedom, but their families' differences keep them apart.", 6),
        ("13th", 2016, "Documentary", 100, 8.2, "An in-depth look at the prison system in the United States and how it reveals the nation's history of racial inequality.", 7),
        ("John Wick", 2014, "Action", 101, 7.4, "An ex-hit-man comes out of retirement to track down the gangsters that killed his dog and took everything from him.", 8),
        ("Hereditary", 2018, "Horror", 127, 7.3, "A grieving family is haunted by tragic and disturbing occurrences after the death of their secretive grandmother.", 9),
        ("La La Land", 2016, "Romance", 128, 8.0, "While navigating their careers in Los Angeles, a pianist and an actress fall in love while attempting to reconcile their aspirations for the future.", 10),
        ("The Grand Budapest Hotel", 2014, "Comedy", 99, 8.1, "A writer encounters the owner of an aging high-class hotel, who tells him of his early years serving as a lobby boy.", 11),
        ("Moonlight", 2016, "Drama", 111, 7.4, "A young African-American man grapples with his identity and sexuality while experiencing the everyday struggles of childhood, adolescence, and adulthood.", 12),
        ("Arrival", 2016, "Sci-Fi", 116, 7.9, "A linguist works with the military to communicate with alien lifeforms after twelve mysterious spacecraft appear around the world.", 13),
        ("Mad Max: Fury Road", 2015, "Action", 120, 8.1, "In a post-apocalyptic wasteland, a woman rebels against a tyrannical ruler in search of her homeland with the aid of a group of female prisoners and a lone drifter.", 14),
        ("A Quiet Place", 2018, "Horror", 90, 7.5, "A family is forced to live in silence while hiding from creatures that hunt by sound.", 15),
        ("The Social Network", 2010, "Drama", 120, 7.8, "The story of how Harvard student Mark Zuckerberg created the social networking site Facebook.", 16),
        ("Knives Out", 2019, "Thriller", 130, 7.9, "A detective investigates the death of a patriarch of an eccentric, combative family.", 17),
        ("Goodfellas", 1990, "Drama", 146, 8.7, "The story of Henry Hill and his life in the mob, covering his relationship with his wife Karen Hill and his mob partners.", 18),
        ("Little Women", 2019, "Romance", 135, 7.8, "Jo March reflects back and forth on her life, telling the beloved story of the March sisters.", 19),
        ("Do the Right Thing", 1989, "Drama", 120, 8.0, "On the hottest day of the year on a street in Brooklyn, everyone's simmering tensions erupt into violence.", 20),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO Movies (title, release_year, genre, runtime, rating, description, director_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        movies,
    )

    # --- Sample Actors ---
    actors = [
        ("Leonardo DiCaprio",), ("Joseph Gordon-Levitt",), ("Elliot Page",),
        ("Christian Bale",), ("Heath Ledger",), ("Aaron Eckhart",),
        ("Matthew McConaughey",), ("Anne Hathaway",), ("Jessica Chastain",),
        ("Song Kang-ho",), ("Lee Sun-kyun",), ("Cho Yeo-jeong",),
        ("Tim Robbins",), ("Morgan Freeman",),
        ("Jonah Hill",), ("Michael Cera",),
        ("Daniel Kaluuya",), ("Allison Williams",),
        ("Ryan Gosling",), ("Rachel McAdams",),
        ("Keanu Reeves",),
        ("Toni Collette",),
        ("Emma Stone",),
        ("Ralph Fiennes",),
        ("Mahershala Ali",), ("Trevante Rhodes",),
        ("Amy Adams",), ("Jeremy Renner",),
        ("Tom Hardy",), ("Charlize Theron",),
        ("Emily Blunt",),
        ("Jesse Eisenberg",), ("Andrew Garfield",),
        ("Daniel Craig",), ("Chris Evans",), ("Ana de Armas",),
        ("Robert De Niro",), ("Ray Liotta",), ("Joe Pesci",),
        ("Saoirse Ronan",), ("Florence Pugh",), ("Timothée Chalamet",),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO Actors (name) VALUES (?)",
        actors,
    )

    # --- MovieActors (junction table) ---
    movie_actors = [
        (1, 1), (1, 2), (1, 3),       # Inception
        (2, 4), (2, 5), (2, 6),       # The Dark Knight
        (3, 7), (3, 8), (3, 9),       # Interstellar
        (4, 10), (4, 11), (4, 12),    # Parasite
        (5, 13), (5, 14),             # Shawshank
        (6, 15), (6, 16),             # Superbad
        (7, 17), (7, 18),             # Get Out
        (8, 19), (8, 20),             # The Notebook
        (10, 21),                      # John Wick
        (11, 22),                      # Hereditary
        (12, 19), (12, 23),           # La La Land
        (13, 24),                      # Grand Budapest Hotel
        (14, 25), (14, 26),           # Moonlight
        (15, 27), (15, 28),           # Arrival
        (16, 29), (16, 30),           # Mad Max
        (17, 31),                      # A Quiet Place
        (18, 32), (18, 33),           # Social Network
        (19, 34), (19, 35), (19, 36), # Knives Out
        (20, 37), (20, 38), (20, 39), # Goodfellas
        (21, 40), (21, 41), (21, 42), # Little Women
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO MovieActors (movie_id, actor_id) VALUES (?, ?)",
        movie_actors,
    )

    # --- Sample Ratings ---
    ratings = [
        (1, "filmfan99", 9.0, "Mind-bending masterpiece. Nolan at his best."),
        (1, "cinephile_k", 8.5, "Great concept but the ending left me wanting more."),
        (2, "darkknightfan", 9.5, "Heath Ledger's Joker is legendary."),
        (2, "moviebuff22", 8.8, "Best superhero movie ever made."),
        (5, "classicmovielover", 10.0, "Perfect film. Timeless."),
        (5, "reviewer_m", 9.0, "Morgan Freeman carries every scene."),
        (4, "worldcinema", 9.0, "Brilliant social commentary wrapped in a thriller."),
        (7, "horrorhead", 8.0, "Jordan Peele redefined horror."),
        (12, "musiclover", 8.5, "Beautiful cinematography and music."),
        (16, "actionjunkie", 8.5, "Non-stop adrenaline from start to finish."),
        (20, "classiccinema", 9.0, "Scorsese's best work alongside Taxi Driver."),
        (3, "scifi_nerd", 9.2, "The docking scene still gives me chills."),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO Ratings (movie_id, username, score, review) VALUES (?, ?, ?, ?)",
        ratings,
    )

    conn.commit()
    conn.close()
    print("Database initialized successfully with sample data!")


if __name__ == "__main__":
    init()
