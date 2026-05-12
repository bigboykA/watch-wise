from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)
DATABASE = "netflix.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@app.route("/")
def index():
    conn = get_db()

    genre = request.args.get("genre", "")
    content_rating = request.args.get("content_rating", "")
    title_type = request.args.get("type", "")
    year_from = request.args.get("year_from", "")
    year_to = request.args.get("year_to", "")
    search = request.args.get("search", "")

    query = """
        SELECT DISTINCT t.show_id, t.type, t.title, t.date_added,
               t.release_year, t.rating, t.duration, t.description
        FROM titles t
    """
    joins = []
    conditions = ["1=1"]
    params = []

    if genre:
        joins.append("JOIN title_genres tg ON t.show_id = tg.show_id")
        joins.append("JOIN genres g ON tg.genre_id = g.genre_id")
        conditions.append("g.name = ?")
        params.append(genre)

    if content_rating:
        conditions.append("t.rating = ?")
        params.append(content_rating)

    if title_type:
        conditions.append("t.type = ?")
        params.append(title_type)

    if year_from:
        conditions.append("t.release_year >= ?")
        params.append(int(year_from))

    if year_to:
        conditions.append("t.release_year <= ?")
        params.append(int(year_to))

    if search:
        conditions.append("t.title LIKE ?")
        params.append(f"%{search}%")

    full_query = query + " " + " ".join(joins) + " WHERE " + " AND ".join(conditions)
    full_query += " ORDER BY t.release_year DESC, t.title ASC LIMIT 60"

    titles = conn.execute(full_query, params).fetchall()

    genres = conn.execute("SELECT name FROM genres ORDER BY name").fetchall()
    genre_list = [g["name"] for g in genres]

    ratings = conn.execute(
        "SELECT DISTINCT rating FROM titles WHERE rating IS NOT NULL AND rating != '' ORDER BY rating"
    ).fetchall()
    rating_list = [r["rating"] for r in ratings]

    total = conn.execute("SELECT COUNT(*) as cnt FROM titles").fetchone()["cnt"]

    conn.close()

    return render_template(
        "index.html",
        titles=titles,
        genres=genre_list,
        ratings=rating_list,
        total=total,
        selected_genre=genre,
        selected_rating=content_rating,
        selected_type=title_type,
        year_from=year_from,
        year_to=year_to,
        search=search,
    )


@app.route("/title/<show_id>")
def title_detail(show_id):
    conn = get_db()

    title = conn.execute(
        "SELECT * FROM titles WHERE show_id = ?", (show_id,)
    ).fetchone()

    directors = conn.execute("""
        SELECT d.name FROM directors d
        JOIN title_directors td ON d.director_id = td.director_id
        WHERE td.show_id = ?
    """, (show_id,)).fetchall()

    actors = conn.execute("""
        SELECT a.name FROM actors a
        JOIN title_actors ta ON a.actor_id = ta.actor_id
        WHERE ta.show_id = ?
    """, (show_id,)).fetchall()

    genres = conn.execute("""
        SELECT g.name FROM genres g
        JOIN title_genres tg ON g.genre_id = tg.genre_id
        WHERE tg.show_id = ?
    """, (show_id,)).fetchall()

    countries = conn.execute("""
        SELECT c.name FROM countries c
        JOIN title_countries tc ON c.country_id = tc.country_id
        WHERE tc.show_id = ?
    """, (show_id,)).fetchall()

    conn.close()

    return render_template(
        "detail.html",
        title=title,
        directors=directors,
        actors=actors,
        genres=genres,
        countries=countries,
    )


if __name__ == "__main__":
    app.run(debug=True)
