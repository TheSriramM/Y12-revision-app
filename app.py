from flask import Flask, session, request, render_template, redirect, url_for, g
import sqlite3
import os

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static',
)
DATABASE = "database.db"

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def home():
    return render_template("home.html",)

if __name__ == "__main__":
    app.run(debug=True)