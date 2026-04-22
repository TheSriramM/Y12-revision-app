from flask import Flask, session, request, render_template, redirect, url_for, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static',
)
app.secret_key = 'my_secret_key'  # Add this for session management
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
def index():
    return render_template("home.html")

@app.route('/home')
def home():
    return render_template("home.html",)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['username']  # can be username OR email
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT id, username, password_hash 
            FROM users 
            WHERE username = ? OR email = ?
        """, (identifier, identifier))

        user = cursor.fetchone()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            return "Invalid login"

    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        db = get_db()
        cursor = db.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)",
                (email, username, hashed_password)
            )
            db.commit()

            user_id = cursor.lastrowid
            session['user_id'] = user_id
            session['username'] = username

        except sqlite3.IntegrityError:
            return "Username or email already exists"

        return redirect(url_for('login'))

    return render_template("register.html")

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))  # block access

    return render_template("dashboard.html", username=session['username'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)