from flask import Flask, session, request, render_template, redirect, url_for, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static',
)
app.secret_key = 'wowow'
DATABASE = "database.db"
example_quiz = [
    {
        "question": "What is H2O?",
        "options": ["Water", "Oxygen", "Salt", "Hydrogen"],
        "answer": "Water"
    },

    {
        "question": "What is the pH of a neutral solution?",
        "options": ["7", "1", "14", "3"],
        "answer": "7"
    }
]

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

        # Backend validation to make sure the user doesn't enter more or less than the limit
        # Doesn't show due to the maxlength set in HTML

        if len(username) > 30:
            flash("Username too long (max 30 characters)")
            return redirect(url_for('register'))
        
        if len(password) > 64:
            flash("Password too long (max 64 characters)")
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash("Password must be at least 6 characters long")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        db = get_db()
        cursor = db.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)",
                (email, username, hashed_password)
            )
            db.commit()

            # Store the variables using session
            user_id = cursor.lastrowid
            session['user_id'] = user_id
            session['username'] = username

        except sqlite3.IntegrityError:
            return "Username or email already exists"

        return redirect(url_for('login'))

    return render_template("register.html")

@app.route('/features')
def features():
    return render_template("features.html")

@app.route('/flashcards')
def flashcards():
    return render_template("flashcards.html")

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    result = ""

    if 'cur_question' not in session:
        session['cur_question'] = 0
        session['correct'] = 0
        session['incorrect'] = 0

    cur_question = session['cur_question']

    if request.method == "POST":
        selected = request.form.get("answer")
        correct_answer = example_quiz[cur_question]["answer"]

        if selected == correct_answer:
            result = "Correct!"
            # The second parameter is just in case the session variable has not been set or defined properly in which case 0 will be returned
            session['correct'] = session.get('correct', 0) + 1
        else:
            result = "Incorrect"
            # The second parameter is just in case the session variable has not been set or defined properly in which case 0 will be returned
            session['incorrect'] = session.get('incorrect', 0) + 1

        cur_question += 1
        session['cur_question'] = cur_question

    if cur_question >= len(example_quiz):
        return redirect(url_for('quiz_complete'))

    question = example_quiz[cur_question]
    return render_template("quiz.html", question=question, result=result)

@app.route('/quiz_complete')
def quiz_complete():
    correct = session.get('correct', 0)
    incorrect = session.get('incorrect', 0)
    return render_template("quiz_complete.html", correct=correct, incorrect=incorrect)

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