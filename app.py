from flask import Flask, session, request, render_template, redirect, url_for, g, flash, jsonify
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

example_flashcards = [
    {
        "question": "What is H2CO3?",
        "answer": "Carbonic acid"
    },

    {
        "question": "What is H2O?",
        "answer": "Water"
    },

    {
        "question": "pH of neutral solution?",
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
            flash("Invalid login")
            return render_template("login.html", identifier=identifier)
        
    # Sets the username input value to identifier which means the username/email field remains filled
    return render_template("login.html", identifier="")

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

@app.route('/flashcards', methods=["GET", "POST"])
def flashcards():
    # initialize session values only it doesn't reset
    # the current index or answer visibility on every request
    if 'cur_index' not in session:
        session['cur_index'] = 0
    session.setdefault('showing_answer', False)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "flip":
            session['showing_answer'] = not session['showing_answer']

        elif action == "next":
            if session['cur_index'] < len(example_flashcards) - 1:
                session['cur_index'] += 1
                
            session['showing_answer'] = False
        
        elif action == "prev":
            if session['cur_index'] > 0:
                session['cur_index'] -= 1

            session['showing_answer'] = False
        
    current_card = example_flashcards[session['cur_index']]

    if session['showing_answer']:
        card_text = current_card["answer"]
    else:
        card_text = current_card["question"]


    # Return JSON for AJAX requests (just the data for JS)
    # This is a dictionary for the js
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'card_text': card_text,
            'showing_answer': session['showing_answer'],
            'current_index': session['cur_index'],
            'total_cards': len(example_flashcards)
        })
    
    return render_template(
        "flashcards.html",
        card_text=card_text,
        current_index=session['cur_index'],
        total_cards=len(example_flashcards)
    )

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

    # Get the number of decks the user has created
    db = get_db()
    cursor = db.cursor()
    
    # Query the total number of decks for this user
    cursor.execute("""
        SELECT COUNT(*) FROM topics WHERE user_id = ?
    """, (session['user_id'],))
    
    deck_count = cursor.fetchone()[0]

    return render_template("dashboard.html", username=session['username'], deck_count=deck_count)

@app.route('/decks')
def decks():
    if 'username' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT id, name, description, subject FROM topics WHERE user_id = ?",
        (session['user_id'],)
    )
    rows = cursor.fetchall()

    decks = [
        {
            "id": topic[0],
            "name": topic[1],
            "description": topic[2] or "",
            "subject": topic[3] or ""
        }
        for topic in rows
    ]

    return render_template("decks.html", decks=decks)

@app.route('/edit_deck/<int:deck_id>')
def edit_deck(deck_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, name, description, subject, cover_color, is_public FROM topics WHERE id = ? AND user_id = ?",
        (deck_id, session['user_id'])
    )
    deck = cursor.fetchone()

    if not deck:
        flash("Deck not found.")
        return redirect(url_for('decks'))

    form_data = {
        "deck_id": deck[0],
        "deck_name": deck[1],
        "description": deck[2] or "",
        "subject": deck[3] or "",
        "cover_color": deck[4] or "#2E90E5",
        "visibility": "public" if deck[5] else "private"
    }

    return render_template("edit_deck.html", form_data=form_data)

@app.route('/create_deck', methods=['GET', 'POST'])
def create_deck():

    # If the user tries to access this page without logging in through the modifying the url
    if 'username' not in session:
        return redirect(url_for('login'))

    # The fields
    form_data = {
        "deck_name": "",
        "subject": "",
        "description": "",
        "cover_color": "",
        "visibility": "private"
    }

    # Get what the user entered as the input for each field
    if request.method == 'POST':
        deck_name = request.form.get('deck_name', '').strip()
        subject = request.form.get('subject', '').strip()
        description = request.form.get('description', '').strip()
        cover_color = request.form.get('cover_color', '').strip() or "#2E90E5"
        visibility = request.form.get('visibility', 'private')

        form_data.update({
            "deck_name": deck_name,
            "subject": subject,
            "description": description,
            "cover_color": cover_color,
            "visibility": visibility,
        })

        if not deck_name or not subject:
            flash("Deck name and subject are required.")
            return render_template("create_deck.html", form_data=form_data)

        db = get_db()
        cursor = db.cursor()

        # Check if the subject exists
        cursor.execute(
            "SELECT 1 FROM topics WHERE lower(subject) = lower(?)",
            (subject,)
        )
        if cursor.fetchone():
            flash("That subject already exists. Please choose a different subject name.")
            return render_template("create_deck.html", form_data=form_data)

        cursor.execute(
            """
            INSERT INTO topics (name, user_id, description, subject, cover_color, is_public)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (deck_name, session['user_id'], description or None, subject, cover_color, 1 if visibility == 'public' else 0)
        )
        
        # Modifies the database
        db.commit()

        # Notification for now
        flash(f"Deck '{deck_name}' created successfully.")
        return redirect(url_for('decks'))

    return render_template("create_deck.html", form_data=form_data)
    
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)