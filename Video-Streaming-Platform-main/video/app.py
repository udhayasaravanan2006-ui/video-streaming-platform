 
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, abort
from werkzeug.utils import secure_filename

# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

# Project root is the parent directory of the video folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMPLATE_FOLDER = os.path.join(BASE_DIR, "templates")
STATIC_FOLDER = os.path.join(BASE_DIR, "static")
UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, "uploads")
DATABASE = os.path.join(BASE_DIR, "videos.db")

# --------------------------------------------------
# FLASK CONFIGURATION
# --------------------------------------------------

app = Flask(
    __name__,
    template_folder=TEMPLATE_FOLDER,
    static_folder=STATIC_FOLDER
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1 GB upload limit

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                filename TEXT NOT NULL
            )
        """)


init_db()


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def index():
    with get_db_connection() as conn:
        videos = conn.execute(
            "SELECT * FROM videos ORDER BY id DESC"
        ).fetchall()

    return render_template("index.html", videos=videos)


# --------------------------------------------------
# UPLOAD VIDEO
# --------------------------------------------------

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        uploaded_file = request.files.get("video")

        if not title:
            return "Please enter a video title.", 400

        if not uploaded_file or not uploaded_file.filename:
            return "Please select a video file.", 400

        filename = secure_filename(uploaded_file.filename)

        if not filename:
            return "Invalid filename.", 400

        # Avoid overwriting an existing uploaded file
        name, extension = os.path.splitext(filename)
        candidate = filename
        counter = 1

        while os.path.exists(os.path.join(UPLOAD_FOLDER, candidate)):
            candidate = f"{name}_{counter}{extension}"
            counter += 1

        file_path = os.path.join(UPLOAD_FOLDER, candidate)

        try:
            uploaded_file.save(file_path)

            with get_db_connection() as conn:
                conn.execute(
                    "INSERT INTO videos (title, filename) VALUES (?, ?)",
                    (title, candidate)
                )

        except Exception:
            if os.path.exists(file_path):
                os.remove(file_path)
            app.logger.exception("Video upload failed")
            return "Video upload failed. Please check the server logs.", 500

        return redirect(url_for("index"))

    return render_template("upload.html")


# --------------------------------------------------
# WATCH VIDEO
# --------------------------------------------------

@app.route("/watch/<int:video_id>")
def watch(video_id):
    with get_db_connection() as conn:
        video = conn.execute(
            "SELECT * FROM videos WHERE id = ?",
            (video_id,)
        ).fetchone()

    if video is None:
        abort(404)

    return render_template("watch.html", video=video)


# --------------------------------------------------
# SERVE UPLOADED VIDEO
# --------------------------------------------------

@app.route("/videos/<path:filename>")
def serve_video(filename):
    return app.send_static_file(
        os.path.relpath(
            os.path.join(UPLOAD_FOLDER, filename),
            STATIC_FOLDER
        ).replace("\\", "/")
    )


# --------------------------------------------------
# DELETE VIDEO
# --------------------------------------------------

@app.route("/delete/<int:video_id>", methods=["POST"])
def delete(video_id):
    with get_db_connection() as conn:
        video = conn.execute(
            "SELECT filename FROM videos WHERE id = ?",
            (video_id,)
        ).fetchone()

        if video is None:
            abort(404)

        conn.execute(
            "DELETE FROM videos WHERE id = ?",
            (video_id,)
        )

    file_path = os.path.join(UPLOAD_FOLDER, video["filename"])

    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
    except OSError:
        app.logger.exception("Could not remove uploaded video file")

    return redirect(url_for("index"))


# --------------------------------------------------
# ERROR HANDLERS
# --------------------------------------------------

@app.errorhandler(404)
def not_found(error):
    return "Page or video not found.", 404


@app.errorhandler(413)
def file_too_large(error):
    return "Video is too large. Maximum upload size is 1 GB.", 413


# --------------------------------------------------
# LOCAL DEVELOPMENT
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=False)
