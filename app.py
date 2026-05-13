from flask import Flask, abort, flash, g, redirect, render_template, request, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = "watchwise-csc310-demo-secret"
DATABASE = "netflix.db"
# Single-user app: favorites/collections DB rows use this label.
APP_USER = "guest"
app.jinja_env.globals["APP_USER"] = APP_USER


# ----------- DB connection (request-scoped via flask.g) -----------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ----------- Small helpers -----------

def field(name, default=""):
    """Read a form field, coerce to stripped string."""
    return (request.form.get(name) or default).strip()


def get_or_redirect(query, params, error_msg, redirect_to="index"):
    """Fetch one row or flash + abort with a redirect. Caller stays one-liner."""
    row = get_db().execute(query, params).fetchone()
    if row is None:
        flash(error_msg)
        abort(redirect(url_for(redirect_to)))
    return row


def parse_score(score_str):
    """Return float in [0, 10] or None if invalid."""
    try:
        v = float((score_str or "").strip())
        return v if 0 <= v <= 10 else None
    except ValueError:
        return None


def parse_optional_int(s):
    """Return (int_or_None, error_msg_or_None). Empty input -> (None, None)."""
    s = (s or "").strip()
    if not s:
        return None, None
    try:
        return int(s), None
    except ValueError:
        return None, "Must be a number."


def collection_owned(collection_id, user):
    return get_db().execute(
        "SELECT 1 FROM collections WHERE collection_id = ? AND user_label = ?",
        (collection_id, user),
    ).fetchone() is not None


# ----------- Schema for the CRUD-only tables we added on top of netflix.db -----------

def init_extra_tables():
    """Create reviews / favorites / collections tables on startup (idempotent)."""
    with app.app_context():
        get_db().executescript("""
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
        get_db().commit()


# ----------- BROWSE -----------

@app.route("/")
def index():
    db = get_db()

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
    joins, conditions, params = [], ["1=1"], []

    if genre:
        joins.append("JOIN title_genres tg ON t.show_id = tg.show_id")
        joins.append("JOIN genres g ON tg.genre_id = g.genre_id")
        conditions.append("g.name = ?")
        params.append(genre)
    if content_rating:
        conditions.append("t.rating = ?"); params.append(content_rating)
    if title_type:
        conditions.append("t.type = ?"); params.append(title_type)
    if year_from:
        conditions.append("t.release_year >= ?"); params.append(int(year_from))
    if year_to:
        conditions.append("t.release_year <= ?"); params.append(int(year_to))
    if search:
        conditions.append("t.title LIKE ?"); params.append(f"%{search}%")

    full_query = (
        query + " " + " ".join(joins) + " WHERE " + " AND ".join(conditions)
        + " ORDER BY t.release_year DESC, t.title ASC LIMIT 60"
    )
    titles = db.execute(full_query, params).fetchall()

    genre_list = [g["name"] for g in db.execute("SELECT name FROM genres ORDER BY name")]
    rating_list = [r["rating"] for r in db.execute(
        "SELECT DISTINCT rating FROM titles WHERE rating IS NOT NULL AND rating != '' ORDER BY rating"
    )]
    total = db.execute("SELECT COUNT(*) AS cnt FROM titles").fetchone()["cnt"]

    return render_template(
        "index.html",
        titles=titles, genres=genre_list, ratings=rating_list, total=total,
        selected_genre=genre, selected_rating=content_rating, selected_type=title_type,
        year_from=year_from, year_to=year_to, search=search,
    )


@app.route("/title/<show_id>")
def title_detail(show_id):
    db = get_db()
    title = get_or_redirect(
        "SELECT * FROM titles WHERE show_id = ?", (show_id,),
        "That title doesn't exist.",
    )

    directors = db.execute("""
        SELECT d.name FROM directors d
        JOIN title_directors td ON d.director_id = td.director_id
        WHERE td.show_id = ?
    """, (show_id,)).fetchall()

    actors = db.execute("""
        SELECT a.name FROM actors a
        JOIN title_actors ta ON a.actor_id = ta.actor_id
        WHERE ta.show_id = ?
    """, (show_id,)).fetchall()

    genres = db.execute("""
        SELECT g.name FROM genres g
        JOIN title_genres tg ON g.genre_id = tg.genre_id
        WHERE tg.show_id = ?
    """, (show_id,)).fetchall()

    countries = db.execute("""
        SELECT c.name FROM countries c
        JOIN title_countries tc ON c.country_id = tc.country_id
        WHERE tc.show_id = ?
    """, (show_id,)).fetchall()

    reviews = db.execute("""
        SELECT review_id, username, score, review_text, created_at
        FROM reviews WHERE show_id = ? ORDER BY created_at DESC
    """, (show_id,)).fetchall()

    is_favorited = db.execute(
        "SELECT 1 FROM favorites WHERE user_label = ? AND show_id = ?",
        (APP_USER, show_id),
    ).fetchone() is not None

    user_collections = db.execute(
        "SELECT collection_id, name FROM collections WHERE user_label = ? ORDER BY name",
        (APP_USER,),
    ).fetchall()

    in_collection_ids = {
        row["collection_id"] for row in db.execute(
            """SELECT ci.collection_id FROM collection_items ci
               JOIN collections c ON c.collection_id = ci.collection_id
               WHERE c.user_label = ? AND ci.show_id = ?""",
            (APP_USER, show_id),
        )
    }

    return render_template(
        "detail.html",
        title=title, directors=directors, actors=actors, genres=genres,
        countries=countries, reviews=reviews, is_favorited=is_favorited,
        user_collections=user_collections, in_collection_ids=in_collection_ids,
    )


# ----------- REVIEWS (INSERT / UPDATE / DELETE) -----------

@app.route("/title/<show_id>/review", methods=["POST"])
def add_review(show_id):
    username = (field("username") or APP_USER)[:50]
    score_val = parse_score(field("score"))
    if score_val is None:
        flash("Score must be a number between 0 and 10.")
        return redirect(url_for("title_detail", show_id=show_id))
    if not username:
        flash("Username is required.")
        return redirect(url_for("title_detail", show_id=show_id))

    db = get_db()
    db.execute(
        "INSERT INTO reviews (show_id, username, score, review_text) VALUES (?, ?, ?, ?)",
        (show_id, username, score_val, field("review_text")),
    )
    db.commit()
    flash("Review posted!")
    return redirect(url_for("title_detail", show_id=show_id))


@app.route("/review/<int:review_id>/edit", methods=["POST"])
def edit_review(review_id):
    score_val = parse_score(field("score"))
    if score_val is None:
        flash("Score must be a number between 0 and 10.")
        return redirect(request.referrer or url_for("index"))

    row = get_or_redirect(
        "SELECT show_id FROM reviews WHERE review_id = ?", (review_id,),
        "Review not found.",
    )
    db = get_db()
    db.execute(
        "UPDATE reviews SET score = ?, review_text = ? WHERE review_id = ?",
        (score_val, field("review_text"), review_id),
    )
    db.commit()
    flash("Review updated.")
    return redirect(url_for("title_detail", show_id=row["show_id"]))


@app.route("/review/<int:review_id>/delete", methods=["POST"])
def delete_review(review_id):
    row = get_or_redirect(
        "SELECT show_id FROM reviews WHERE review_id = ?", (review_id,),
        "Review not found.",
    )
    db = get_db()
    db.execute("DELETE FROM reviews WHERE review_id = ?", (review_id,))
    db.commit()
    flash("Review deleted.")
    return redirect(url_for("title_detail", show_id=row["show_id"]))


# ----------- FAVORITES (INSERT / DELETE) -----------

@app.route("/title/<show_id>/favorite", methods=["POST"])
def toggle_favorite(show_id):
    db = get_db()
    exists = db.execute(
        "SELECT 1 FROM favorites WHERE user_label = ? AND show_id = ?",
        (APP_USER, show_id),
    ).fetchone()
    if exists:
        db.execute("DELETE FROM favorites WHERE user_label = ? AND show_id = ?",
                   (APP_USER, show_id))
        flash("Removed from favorites.")
    else:
        db.execute("INSERT INTO favorites (user_label, show_id) VALUES (?, ?)",
                   (APP_USER, show_id))
        flash("Added to favorites!")
    db.commit()
    return redirect(request.referrer or url_for("title_detail", show_id=show_id))


@app.route("/favorites")
def favorites():
    rows = get_db().execute("""
        SELECT t.show_id, t.title, t.type, t.release_year, t.rating, t.duration, t.description,
               f.added_at
        FROM favorites f
        JOIN titles t ON t.show_id = f.show_id
        WHERE f.user_label = ?
        ORDER BY f.added_at DESC
    """, (APP_USER,)).fetchall()
    return render_template("favorites.html", titles=rows)


# ----------- EDIT TITLE METADATA (UPDATE) -----------

@app.route("/title/<show_id>/edit", methods=["GET", "POST"])
def edit_title(show_id):
    title = get_or_redirect(
        "SELECT * FROM titles WHERE show_id = ?", (show_id,),
        "Title not found.",
    )

    if request.method == "POST":
        new_title = field("title")
        if not new_title:
            flash("Title cannot be empty.")
            return redirect(url_for("edit_title", show_id=show_id))

        year_val, year_err = parse_optional_int(field("release_year"))
        if year_err:
            flash(f"Release year: {year_err}")
            return redirect(url_for("edit_title", show_id=show_id))

        db = get_db()
        db.execute("""
            UPDATE titles
            SET title = ?, type = ?, release_year = ?, rating = ?, duration = ?, description = ?
            WHERE show_id = ?
        """, (
            new_title, field("type") or title["type"], year_val,
            field("rating"), field("duration"), field("description"), show_id,
        ))
        db.commit()
        flash("Title updated.")
        return redirect(url_for("title_detail", show_id=show_id))

    return render_template("edit_title.html", title=title)


# ----------- ADD A NEW TITLE (INSERT into titles + title_genres) -----------

def next_user_show_id():
    """Generate the next user-added show_id like 'u1', 'u2', ..."""
    row = get_db().execute(
        "SELECT show_id FROM titles WHERE show_id LIKE 'u%' "
        "ORDER BY CAST(SUBSTR(show_id, 2) AS INTEGER) DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return "u1"
    return f"u{int(row['show_id'][1:]) + 1}"


@app.route("/add-title", methods=["GET", "POST"])
def add_title():
    if request.method == "POST":
        title_text = field("title")
        if not title_text:
            flash("Title is required.")
            return redirect(url_for("add_title"))

        year_val, year_err = parse_optional_int(field("release_year"))
        if year_err:
            flash(f"Release year: {year_err}")
            return redirect(url_for("add_title"))

        db = get_db()
        new_id = next_user_show_id()
        db.execute("""
            INSERT INTO titles (show_id, type, title, release_year, rating, duration, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            new_id, field("type") or "Movie", title_text, year_val,
            field("rating"), field("duration"), field("description"),
        ))

        for genre_name in request.form.getlist("genres"):
            row = db.execute("SELECT genre_id FROM genres WHERE name = ?", (genre_name,)).fetchone()
            if row:
                db.execute(
                    "INSERT OR IGNORE INTO title_genres (show_id, genre_id) VALUES (?, ?)",
                    (new_id, row["genre_id"]),
                )

        db.commit()
        flash(f"Added '{title_text}' to the catalog.")
        return redirect(url_for("title_detail", show_id=new_id))

    genres = [g["name"] for g in get_db().execute("SELECT name FROM genres ORDER BY name")]
    return render_template("add_title.html", genres=genres)


# ----------- DELETE A TITLE (DELETE titles + junction cleanup) -----------

@app.route("/title/<show_id>/delete", methods=["POST"])
def delete_title(show_id):
    title = get_or_redirect(
        "SELECT title FROM titles WHERE show_id = ?", (show_id,),
        "Title not found.",
    )
    db = get_db()
    # Junction tables without ON DELETE CASCADE from titles.
    db.execute("DELETE FROM title_actors    WHERE show_id = ?", (show_id,))
    db.execute("DELETE FROM title_directors WHERE show_id = ?", (show_id,))
    db.execute("DELETE FROM title_genres    WHERE show_id = ?", (show_id,))
    db.execute("DELETE FROM title_countries WHERE show_id = ?", (show_id,))
    # reviews, favorites, collection_items reference titles with ON DELETE CASCADE.
    db.execute("DELETE FROM titles WHERE show_id = ?", (show_id,))
    db.commit()
    flash(f"Deleted '{title['title']}'.")
    return redirect(url_for("index"))


# ----------- CUSTOM COLLECTIONS (full CRUD) -----------

@app.route("/collections")
def collections_list():
    rows = get_db().execute("""
        SELECT c.collection_id, c.name, c.created_at,
               COUNT(ci.show_id) AS item_count
        FROM collections c
        LEFT JOIN collection_items ci ON ci.collection_id = c.collection_id
        WHERE c.user_label = ?
        GROUP BY c.collection_id
        ORDER BY c.created_at DESC
    """, (APP_USER,)).fetchall()
    return render_template("collections.html", collections=rows)


@app.route("/collections/new", methods=["POST"])
def create_collection():
    name = field("name")
    if not name:
        flash("Collection name is required.")
        return redirect(url_for("collections_list"))
    db = get_db()
    db.execute("INSERT INTO collections (user_label, name) VALUES (?, ?)",
               (APP_USER, name[:100]))
    db.commit()
    flash(f"Created collection '{name}'.")
    return redirect(url_for("collections_list"))


@app.route("/collections/<int:collection_id>")
def collection_detail(collection_id):
    collection = get_or_redirect(
        "SELECT * FROM collections WHERE collection_id = ? AND user_label = ?",
        (collection_id, APP_USER),
        "Collection not found.",
        redirect_to="collections_list",
    )
    items = get_db().execute("""
        SELECT t.show_id, t.title, t.type, t.release_year, t.rating, t.duration, t.description
        FROM collection_items ci
        JOIN titles t ON t.show_id = ci.show_id
        WHERE ci.collection_id = ?
        ORDER BY ci.added_at DESC
    """, (collection_id,)).fetchall()
    return render_template("collection_detail.html", collection=collection, items=items)


@app.route("/collections/<int:collection_id>/rename", methods=["POST"])
def rename_collection(collection_id):
    new_name = field("name")
    if not new_name:
        flash("New name is required.")
        return redirect(url_for("collection_detail", collection_id=collection_id))
    db = get_db()
    db.execute(
        "UPDATE collections SET name = ? WHERE collection_id = ? AND user_label = ?",
        (new_name[:100], collection_id, APP_USER),
    )
    db.commit()
    flash("Collection renamed.")
    return redirect(url_for("collection_detail", collection_id=collection_id))


@app.route("/collections/<int:collection_id>/delete", methods=["POST"])
def delete_collection(collection_id):
    db = get_db()
    db.execute(
        "DELETE FROM collections WHERE collection_id = ? AND user_label = ?",
        (collection_id, APP_USER),
    )
    db.commit()
    flash("Collection deleted.")
    return redirect(url_for("collections_list"))


@app.route("/collections/<int:collection_id>/add/<show_id>", methods=["POST"])
def add_to_collection(collection_id, show_id):
    if not collection_owned(collection_id, APP_USER):
        flash("Not your collection.")
        return redirect(request.referrer or url_for("collections_list"))
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO collection_items (collection_id, show_id) VALUES (?, ?)",
        (collection_id, show_id),
    )
    db.commit()
    flash("Added to collection.")
    return redirect(request.referrer or url_for("title_detail", show_id=show_id))


@app.route("/collections/<int:collection_id>/remove/<show_id>", methods=["POST"])
def remove_from_collection(collection_id, show_id):
    if not collection_owned(collection_id, APP_USER):
        flash("Not your collection.")
        return redirect(request.referrer or url_for("collections_list"))
    db = get_db()
    db.execute(
        "DELETE FROM collection_items WHERE collection_id = ? AND show_id = ?",
        (collection_id, show_id),
    )
    db.commit()
    flash("Removed from collection.")
    return redirect(request.referrer or url_for("collection_detail", collection_id=collection_id))


init_extra_tables()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
