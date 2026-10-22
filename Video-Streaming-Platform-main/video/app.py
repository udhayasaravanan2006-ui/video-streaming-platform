
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import sqlite3, os
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = "static/uploads"
DB = "videos.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS videos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        filename TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM videos ORDER BY id DESC")
    videos = cur.fetchall()
    conn.close()
    return render_template("index.html", videos=videos)

@app.route("/upload", methods=["GET","POST"])
def upload():
    if request.method == "POST":
        title = request.form["title"]
        file = request.files["video"]

        if file:
            filename = secure_filename(file.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(path)

            conn = sqlite3.connect(DB)
            cur = conn.cursor()
            cur.execute("INSERT INTO videos(title, filename) VALUES (?,?)",(title, filename))
            conn.commit()
            conn.close()

        return redirect(url_for("index"))
    return render_template("upload.html")

@app.route("/watch/<int:video_id>")
def watch(video_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM videos WHERE id=?", (video_id,))
    video = cur.fetchone()
    conn.close()
    return render_template("watch.html", video=video)

@app.route("/delete/<int:video_id>")
def delete(video_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT filename FROM videos WHERE id=?", (video_id,))
    row = cur.fetchone()

    if row:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, row[0]))
        except:
            pass

    cur.execute("DELETE FROM videos WHERE id=?", (video_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
