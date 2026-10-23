import os
import sqlite3
from datetime import date
from functools import wraps

from flask import (Flask, render_template, request, redirect,
                   url_for, flash, session)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
DB_PATH = os.environ.get(
    "DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.db")
)


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'Medium',
            due_date TEXT,
            done INTEGER NOT NULL DEFAULT 0)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users(
            name TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL)"""
    )
    return conn


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("home"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")
        if not name or len(password) < 4:
            flash("Enter your name and a password of at least 4 characters.", "error")
            return redirect(url_for("login"))
        conn = db()
        row = conn.execute("SELECT * FROM users WHERE name=?", (name,)).fetchone()
        if row is None:
            # first login creates the account
            conn.execute("INSERT INTO users(name, password_hash) VALUES(?,?)",
                         (name, generate_password_hash(password)))
            conn.commit()
        elif not check_password_hash(row["password_hash"], password):
            conn.close()
            flash("Incorrect password for this name.", "error")
            return redirect(url_for("login"))
        conn.close()
        session["user"] = name
        flash(f"Welcome, {name}!", "success")
        return redirect(url_for("home"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    conn = db()
    total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM tasks WHERE done=1").fetchone()[0]
    overdue = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE done=0 AND due_date != '' AND due_date < ?",
        (date.today().isoformat(),),
    ).fetchone()[0]
    conn.close()
    return render_template("greeting.html", total=total, done=done,
                           pending=total - done, overdue=overdue)


@app.route("/add", methods=["GET", "POST"])
@login_required
def add_task():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        if not title or not subject:
            flash("Title and subject are required.", "error")
            return redirect(url_for("add_task"))
        conn = db()
        conn.execute(
            "INSERT INTO tasks(title, subject, priority, due_date) VALUES(?,?,?,?)",
            (title, subject, request.form.get("priority", "Medium"),
             request.form.get("due_date", "")),
        )
        conn.commit()
        conn.close()
        flash("Task added!", "success")
        return redirect(url_for("tasks"))
    return render_template("form.html")


@app.route("/tasks")
@login_required
def tasks():
    conn = db()
    rows = conn.execute("SELECT * FROM tasks ORDER BY done, due_date").fetchall()
    conn.close()
    return render_template("tasks.html", tasks=rows)


@app.route("/complete/<int:task_id>")
@login_required
def complete(task_id):
    conn = db()
    conn.execute("UPDATE tasks SET done=1 WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("tasks"))


@app.route("/delete/<int:task_id>")
@login_required
def delete(task_id):
    conn = db()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("tasks"))


@app.route("/health")
def health():
    # public on purpose: used by the Kubernetes readiness probe
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)