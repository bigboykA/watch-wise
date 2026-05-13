from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "watchwise-csc310-demo-secret"
DATABASE = "netflix.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_extra_tables():
    """Create the new tables for reviews, favorites, and collections.
    Safe to run on every startup (uses IF NOT EXISTS)."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reviews (
            review_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            show_id     VARCHAR(10) NOT NULL REFERENCES titles(show_id) ON DELETE CASCADE,
            username    VARCHAR(50) NOT NULL,
            score       REAL NOT NULL CHECK (score >= 0 AND score <= 10),
            review_text TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS favorites (
            user_label VARCHAR(50) NOT NULL,
            show_id    VARCHAR(10) NOT NULL REFERENCES titles(show_id) ON DELETE CASCADE,
            added_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_label, show_id)
        );

        CREATE TABLE IF NOT EXISTS collections (
            collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_label    VARCHAR(50) NOT NULL,
            name          VARCHAR(100) NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS collection_items (
            collection_id INTEGER NOT NULL REFERENCES collections(collection_id) ON DELETE CASCADE,
            show_id       VARCHAR(10) NOT NULL REFERENCES titles(show_id) ON DELETE CASCADE,
            added_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (collection_id, show_id)
        );
    """)
    conn.commit()
    conn.close()


def current_user():
    """Return the current fake-user label from the session (default: 'guest')."""
    return session.get("user_label", "guest")


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


@app.route("/set-user", methods=["POST"])
def set_user():
    name = (request.form.get("user_label") or "").strip()
    if name:
        session["user_label"] = name[:50]
    return redirect(request.referrer or url_for("index"))


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
    user = current_user()

    title = conn.execute(
        "SELECT * FROM titles WHERE show_id = ?", (show_id,)
    ).fetchone()
    if title is None:
        conn.close()
        flash("That title doesn't exist.")
        return redirect(url_for("index"))

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

    reviews = conn.execute("""
        SELECT review_id, username, score, review_text, created_at
        FROM reviews
        WHERE show_id = ?
        ORDER BY created_at DESC
    """, (show_id,)).fetchall()

    is_favorited = conn.execute(
        "SELECT 1 FROM favorites WHERE user_label = ? AND show_id = ?",
        (user, show_id),
    ).fetchone() is not None

    user_collections = conn.execute(
        "SELECT collection_id, name FROM collections WHERE user_label = ? ORDER BY name",
        (user,),
    ).fetchall()

    in_collection_ids = {
        row["collection_id"] for row in conn.execute(
            """SELECT ci.collection_id FROM collection_items ci
               JOIN collections c ON c.collection_id = ci.collection_id
               WHERE c.user_label = ? AND ci.show_id = ?""",
            (user, show_id),
        ).fetchall()
    }

    conn.close()

    return render_template(
        "detail.html",
        title=title,
        directors=directors,
        actors=actors,
        genres=genres,
        countries=countries,
        reviews=reviews,
        is_favorited=is_favorited,
        user_collections=user_collections,
        in_collection_ids=in_collection_ids,
    )


# ----------- REVIEWS (INSERT / UPDATE / DELETE) -----------

@app.route("/title/<show_id>/review", methods=["POST"])
def add_review(show_id):
    username = (request.form.get("username") or current_user()).strip()[:50]
    score = request.form.get("score", "").strip()
    review_text = (request.form.get("review_text") or "").strip()

    try:
        score_val = float(score)
        if not (0 <= score_val <= 10):
            raise ValueError
    except ValueError:
        flash("Score must be a number between 0 and 10.")
        return redirect(url_for("title_detail", show_id=show_id))

    if not username:
        flash("Username is required.")
        return redirect(url_for("title_detail", show_id=show_id))

    conn = get_db()
    conn.execute(
        "INSERT INTO reviews (show_id, username, score, review_text) VALUES (?, ?, ?, ?)",
        (show_id, username, score_val, review_text),
    )
    conn.commit()
    conn.close()
    flash("Review posted!")
    return redirect(url_for("title_detail", show_id=show_id))


@app.route("/review/<int:review_id>/edit", methods=["POST"])
def edit_review(review_id):
    score = request.form.get("score", "").strip()
    review_text = (request.form.get("review_text") or "").strip()

    try:
        score_val = float(score)
        if not (0 <= score_val <= 10):
            raise ValueError
    except ValueError:
        flash("Score must be a number between 0 and 10.")
        return redirect(request.referrer or url_for("index"))

    conn = get_db()
    row = conn.execute("SELECT show_id FROM reviews WHERE review_id = ?", (review_id,)).fetchone()
    if row is None:
        conn.close()
        flash("Review not found.")
        return redirect(url_for("index"))

    conn.execute(
        "UPDATE reviews SET score = ?, review_text = ? WHERE review_id = ?",
        (score_val, review_text, review_id),
    )
    conn.commit()
    show_id = row["show_id"]
    conn.close()
    flash("Review updated.")
    return redirect(url_for("title_detail", show_id=show_id))


@app.route("/review/<int:review_id>/delete", methods=["POST"])
def delete_review(review_id):
    conn = get_db()
    row = conn.execute("SELECT show_id FROM reviews WHERE review_id = ?", (review_id,)).fetchone()
    if row is None:
        conn.close()
        flash("Review not found.")
        return redirect(url_for("index"))
    conn.execute("DELETE FROM reviews WHERE review_id = ?", (review_id,))
    conn.commit()
    show_id = row["show_id"]
    conn.close()
    flash("Review deleted.")
    return redirect(url_for("title_detail", show_id=show_id))


# ----------- FAVORITES (INSERT / DELETE) -----------

@app.route("/title/<show_id>/favorite", methods=["POST"])
def toggle_favorite(show_id):
    user = current_user()
    conn = get_db()
    exists = conn.execute(
        "SELECT 1 FROM favorites WHERE user_label = ? AND show_id = ?",
        (user, show_id),
    ).fetchone()
    if exists:
        conn.execute(
            "DELETE FROM favorites WHERE user_label = ? AND show_id = ?",
            (user, show_id),
        )
        flash("Removed from favorites.")
    else:
        conn.execute(
            "INSERT INTO favorites (user_label, show_id) VALUES (?, ?)",
            (user, show_id),
        )
        flash("Added to favorites!")
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("title_detail", show_id=show_id))


@app.route("/favorites")
def favorites():
    user = current_user()
    conn = get_db()
    rows = conn.execute("""
        SELECT t.show_id, t.title, t.type, t.release_year, t.rating, t.duration, t.description,
               f.added_at
        FROM favorites f
        JOIN titles t ON t.show_id = f.show_id
        WHERE f.user_label = ?
        ORDER BY f.added_at DESC
    """, (user,)).fetchall()
    conn.close()
    return render_template("favorites.html", titles=rows)


# ----------- EDIT TITLE METADATA (UPDATE) -----------

@app.route("/title/<show_id>/edit", methods=["GET", "POST"])
def edit_title(show_id):
    conn = get_db()
    title = conn.execute("SELECT * FROM titles WHERE show_id = ?", (show_id,)).fetchone()
    if title is None:
        conn.close()
        flash("Title not found.")
        return redirect(url_for("index"))

    if request.method == "POST":
        new_title = (request.form.get("title") or "").strip()
        new_type = request.form.get("type") or title["type"]
        release_year = request.form.get("release_year", "").strip()
        rating = (request.form.get("rating") or "").strip()
        duration = (request.form.get("duration") or "").strip()
        description = (request.form.get("description") or "").strip()

        if not new_title:
            flash("Title cannot be empty.")
            conn.close()
            return redirect(url_for("edit_title", show_id=show_id))

        try:
            year_val = int(release_year) if release_year else None
        except ValueError:
            flash("Release year must be a number.")
            conn.close()
            return redirect(url_for("edit_title", show_id=show_id))

        conn.execute("""
            UPDATE titles
            SET title = ?, type = ?, release_year = ?, rating = ?, duration = ?, description = ?
            WHERE show_id = ?
        """, (new_title, new_type, year_val, rating, duration, description, show_id))
        conn.commit()
        conn.close()
        flash("Title updated.")
        return redirect(url_for("title_detail", show_id=show_id))

    conn.close()
    return render_template("edit_title.html", title=title)


# ----------- ADD A NEW TITLE (INSERT into titles + title_genres) -----------

def next_user_show_id(conn):
    """Generate the next user-added show_id like 'u1', 'u2', ..."""
    row = conn.execute(
        "SELECT show_id FROM titles WHERE show_id LIKE 'u%' "
        "ORDER BY CAST(SUBSTR(show_id, 2) AS INTEGER) DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return "u1"
    try:
        n = int(row["show_id"][1:]) + 1
    except ValueError:
        n = 1
    return f"u{n}"


@app.route("/add-title", methods=["GET", "POST"])
def add_title():
    conn = get_db()

    if request.method == "POST":
        title_text = (request.form.get("title") or "").strip()
        type_val = request.form.get("type") or "Movie"
        release_year = request.form.get("release_year", "").strip()
        rating = (request.form.get("rating") or "").strip()
        duration = (request.form.get("duration") or "").strip()
        description = (request.form.get("description") or "").strip()
        selected_genres = request.form.getlist("genres")

        if not title_text:
            flash("Title is required.")
            conn.close()
            return redirect(url_for("add_title"))

        try:
            year_val = int(release_year) if release_year else None
        except ValueError:
            flash("Release year must be a number.")
            conn.close()
            return redirect(url_for("add_title"))

        new_id = next_user_show_id(conn)
        conn.execute("""
            INSERT INTO titles (show_id, type, title, release_year, rating, duration, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (new_id, type_val, title_text, year_val, rating, duration, description))

        for genre_name in selected_genres:
            row = conn.execute("SELECT genre_id FROM genres WHERE name = ?", (genre_name,)).fetchone()
            if row:
                conn.execute(
                    "INSERT OR IGNORE INTO title_genres (show_id, genre_id) VALUES (?, ?)",
                    (new_id, row["genre_id"]),
                )

        conn.commit()
        conn.close()
        flash(f"Added '{title_text}' to the catalog.")
        return redirect(url_for("title_detail", show_id=new_id))

    genres = conn.execute("SELECT name FROM genres ORDER BY name").fetchall()
    conn.close()
    return render_template("add_title.html", genres=[g["name"] for g in genres])


# ----------- DELETE A TITLE (DELETE titles + junction cleanup) -----------

@app.route("/title/<show_id>/delete", methods=["POST"])
def delete_title(show_id):
    conn = get_db()
    title = conn.execute("SELECT title FROM titles WHERE show_id = ?", (show_id,)).fetchone()
    if title is None:
        conn.close()
        flash("Title not found.")
        return redirect(url_for("index"))

    # Manually cascade across junctions (these tables don't have ON DELETE CASCADE).
    conn.execute("DELETE FROM title_actors    WHERE show_id = ?", (show_id,))
    conn.execute("DELETE FROM title_directors WHERE show_id = ?", (show_id,))
    conn.execute("DELETE FROM title_genres    WHERE show_id = ?", (show_id,))
    conn.execute("DELETE FROM title_countries WHERE show_id = ?", (show_id,))
    # reviews / favorites / collection_items use ON DELETE CASCADE, but be explicit anyway.
    conn.execute("DELETE FROM reviews          WHERE show_id = ?", (show_id,))
    conn.execute("DELETE FROM favorites        WHERE show_id = ?", (show_id,))
    conn.execute("DELETE FROM collection_items WHERE show_id = ?", (show_id,))
    conn.execute("DELETE FROM titles           WHERE show_id = ?", (show_id,))
    conn.commit()
    conn.close()
    flash(f"Deleted '{title['title']}'.")
    return redirect(url_for("index"))


# ----------- CUSTOM COLLECTIONS (full CRUD) -----------

@app.route("/collections", methods=["GET"])
def collections_list():
    user = current_user()
    conn = get_db()
    rows = conn.execute("""
        SELECT c.collection_id, c.name, c.created_at,
               COUNT(ci.show_id) AS item_count
        FROM collections c
        LEFT JOIN collection_items ci ON ci.collection_id = c.collection_id
        WHERE c.user_label = ?
        GROUP BY c.collection_id
        ORDER BY c.created_at DESC
    """, (user,)).fetchall()
    conn.close()
    return render_template("collections.html", collections=rows)


@app.route("/collections/new", methods=["POST"])
def create_collection():
    user = current_user()
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Collection name is required.")
        return redirect(url_for("collections_list"))
    conn = get_db()
    conn.execute(
        "INSERT INTO collections (user_label, name) VALUES (?, ?)",
        (user, name[:100]),
    )
    conn.commit()
    conn.close()
    flash(f"Created collection '{name}'.")
    return redirect(url_for("collections_list"))


@app.route("/collections/<int:collection_id>")
def collection_detail(collection_id):
    user = current_user()
    conn = get_db()
    collection = conn.execute(
        "SELECT * FROM collections WHERE collection_id = ? AND user_label = ?",
        (collection_id, user),
    ).fetchone()
    if collection is None:
        conn.close()
        flash("Collection not found.")
        return redirect(url_for("collections_list"))

    items = conn.execute("""
        SELECT t.show_id, t.title, t.type, t.release_year, t.rating, t.duration, t.description
        FROM collection_items ci
        JOIN titles t ON t.show_id = ci.show_id
        WHERE ci.collection_id = ?
        ORDER BY ci.added_at DESC
    """, (collection_id,)).fetchall()
    conn.close()
    return render_template("collection_detail.html", collection=collection, items=items)


@app.route("/collections/<int:collection_id>/rename", methods=["POST"])
def rename_collection(collection_id):
    user = current_user()
    new_name = (request.form.get("name") or "").strip()
    if not new_name:
        flash("New name is required.")
        return redirect(url_for("collection_detail", collection_id=collection_id))
    conn = get_db()
    conn.execute(
        "UPDATE collections SET name = ? WHERE collection_id = ? AND user_label = ?",
        (new_name[:100], collection_id, user),
    )
    conn.commit()
    conn.close()
    flash("Collection renamed.")
    return redirect(url_for("collection_detail", collection_id=collection_id))


@app.route("/collections/<int:collection_id>/delete", methods=["POST"])
def delete_collection(collection_id):
    user = current_user()
    conn = get_db()
    # ON DELETE CASCADE removes collection_items, but be explicit for clarity.
    conn.execute("DELETE FROM collection_items WHERE collection_id = ?", (collection_id,))
    conn.execute(
        "DELETE FROM collections WHERE collection_id = ? AND user_label = ?",
        (collection_id, user),
    )
    conn.commit()
    conn.close()
    flash("Collection deleted.")
    return redirect(url_for("collections_list"))


@app.route("/collections/<int:collection_id>/add/<show_id>", methods=["POST"])
def add_to_collection(collection_id, show_id):
    user = current_user()
    conn = get_db()
    owner = conn.execute(
        "SELECT 1 FROM collections WHERE collection_id = ? AND user_label = ?",
        (collection_id, user),
    ).fetchone()
    if owner is None:
        conn.close()
        flash("Not your collection.")
        return redirect(request.referrer or url_for("collections_list"))
    conn.execute(
        "INSERT OR IGNORE INTO collection_items (collection_id, show_id) VALUES (?, ?)",
        (collection_id, show_id),
    )
    conn.commit()
    conn.close()
    flash("Added to collection.")
    return redirect(request.referrer or url_for("title_detail", show_id=show_id))


@app.route("/collections/<int:collection_id>/remove/<show_id>", methods=["POST"])
def remove_from_collection(collection_id, show_id):
    user = current_user()
    conn = get_db()
    owner = conn.execute(
        "SELECT 1 FROM collections WHERE collection_id = ? AND user_label = ?",
        (collection_id, user),
    ).fetchone()
    if owner is None:
        conn.close()
        flash("Not your collection.")
        return redirect(request.referrer or url_for("collections_list"))
    conn.execute(
        "DELETE FROM collection_items WHERE collection_id = ? AND show_id = ?",
        (collection_id, show_id),
    )
    conn.commit()
    conn.close()
    flash("Removed from collection.")
    return redirect(request.referrer or url_for("collection_detail", collection_id=collection_id))


init_extra_tables()


if __name__ == "__main__":
    app.run(debug=True)
