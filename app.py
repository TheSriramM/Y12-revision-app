from flask import Flask, session, request, render_template, redirect, url_for, g, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sqlite3
import secrets
import os

load_dotenv()
secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static',
)
app.config['SECRET_KEY'] = secret_key
DATABASE = "database.db"

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # Allows for tuples to be accessed by column name as well as indices
        db.row_factory = sqlite3.Row

    db.execute("PRAGMA foreign_keys = ON")
    return db

# The process of how fcard reviews work and how they are counted
# This is used in the study function
def mark_reviewed_card(cursor, session_data, session_id, card_id, reviewed_cards):
    if card_id in reviewed_cards:
        return False

    reviewed_cards.append(card_id)
    session_data["reviewed_cards"] = reviewed_cards

    cursor.execute("""
        UPDATE study_sessions
        SET cards_reviewed = cards_reviewed + 1
        WHERE session_id = ?
    """, (session_id,))

    return True


def format_study_time(value):
    if not value:
        return "No study sessions yet"

    # If the value returned by SQL is a string, convert it into datetime format
    if isinstance(value, str):
        # Change every space into a capital t which is the standard format needed for the fromisoformat function
        value = datetime.fromisoformat(value.replace(" ", "T"))

    # Get the date today with .date()
    today = datetime.now().date()
    # If last reviewed is today
    if value.date() == today:
        day_label = "Today"

    # One day ago
    elif value.date() == today - timedelta(days=1):
        day_label = "Yesterday"

    # Any other day
    else:
        day_label = value.strftime("%d %b")

    # Format hour from 24 hour format into 12 hour format
    hour = value.hour % 12 or 12
    minute = value.strftime("%M")
    suffix = "AM" if value.hour < 12 else "PM"

    # Return the data in a user friendly format
    # Example: Today at 8:35 PM
    return f"{day_label} at {hour}:{minute} {suffix}"

# Similar to the above function except just return the date without the time
def format_recent_label(value):
    if not value:
        return "Recent"

    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace(" ", "T"))

    today = datetime.now().date()
    if value.date() == today:
        return "Today"
    if value.date() == today - timedelta(days=1):
        return "Yesterday"
    return value.strftime("%d %b")

# Calculate streaks
def calculate_streak(study_dates):
    if not study_dates:
        return 0

    study_set = set(study_dates)

    current = datetime.now().date()
    streak = 0

    if current not in study_set:
        if current - timedelta(days=1) in study_set:
            current = current - timedelta(days=1)
        else:
            return 0
    else:
        current = current

    while current in study_set:
        streak += 1
        current -= timedelta(days=1)

    return streak

# Find the longest ever streak
def calculate_longest_streak(study_dates):
    if not study_dates:
        return 0

    ordered_dates = sorted(study_dates)
    longest = 1
    current_run = 1

    # Find the longest ever streak
    for index in range(1, len(ordered_dates)):
        if ordered_dates[index] == ordered_dates[index - 1] + timedelta(days=1):
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 1

    return longest


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
            flash("Username or email already exists")

        return redirect(url_for('login'))

    return render_template("register.html")


@app.route('/features')
def features():
    return render_template("features.html")

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

    # Query the number of reviews for the user
    cursor.execute("SELECT COUNT(*) FROM study_sessions WHERE user_id = ?;", (session['user_id'],))
    reviews = cursor.fetchone()[0]

    # The study dates
    cursor.execute("""
        SELECT DISTINCT DATE(started_at) AS study_day
        FROM study_sessions
        WHERE user_id = ?
        ORDER BY study_day
    """, (session['user_id'],))

    # Process the data into datetime format
    study_dates = [datetime.strptime(row[0], "%Y-%m-%d").date() for row in cursor.fetchall()]

    streak = calculate_streak(study_dates)

    return render_template("dashboard.html", username=session['username'], deck_count=deck_count, reviews=reviews, streak=streak)


@app.route('/decks')
def decks():
    if 'username' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT id, name, description, subject, cover_color FROM topics WHERE user_id = ?",
        (session['user_id'],)
    )
    rows = cursor.fetchall()

    decks = [
        {
            "id": topic[0],
            "name": topic[1],
            "description": topic[2] or "",
            "subject": topic[3] or "",
            "cover_color": topic[4] or "#2E90E5"
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
        "SELECT id, name, description, subject, cover_color FROM topics WHERE id = ? AND user_id = ?",
        (deck_id, session['user_id'])
    )
    deck = cursor.fetchone()

    if not deck:
        flash("Deck not found.")
        return redirect(url_for('decks'))

    cursor.execute(
        "SELECT id, question, answer FROM flashcards WHERE topic_id = ?",
        (deck_id,)
    )
    flashcards = [
        {"id": row[0], "question": row[1], "answer": row[2]}
        for row in cursor.fetchall()
    ]

    form_data = {
        "deck_id": deck[0],
        "deck_name": deck[1],
        "description": deck[2] or "",
        "subject": deck[3] or "",
    }

    return render_template("edit_deck.html", form_data=form_data, flashcards=flashcards)


@app.route('/add_card/<int:deck_id>', methods=['GET', 'POST'])
def add_card(deck_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, name FROM topics WHERE id = ? AND user_id = ?",
        (deck_id, session['user_id'])
    )
    deck = cursor.fetchone()

    # Preventing user from error if they change the url manually
    if not deck:
        flash("Deck not found.")
        return redirect(url_for('decks'))

    form_data = {
        "question": "",
        "answer": ""
    }

    if request.method == 'POST':
        question = request.form.get('question', '')
        answer = request.form.get('answer', '')
        action = request.form.get('action', 'save')

        form_data.update({
            "question": question,
            "answer": answer,
        })

        # Database insertion
        cursor.execute(
            "INSERT INTO flashcards (topic_id, question, answer) VALUES (?, ?, ?)",
            (deck_id, question, answer)
        )
        db.commit()

        # Let the user know that the flashcard has been added
        flash("Flashcard added successfully.")

        # Reload the same page for the new card to be added
        if action == 'save_add_another':
            form_data = {"question": "", "answer": ""}
            return render_template("add_card.html", deck={"id": deck[0], "name": deck[1]}, form_data=form_data, edit_mode=False)

        return redirect(url_for('edit_deck', deck_id=deck_id))

    return render_template("add_card.html", deck={"id": deck[0], "name": deck[1]}, form_data=form_data, edit_mode=False)


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
    }

    # Get what the user entered as the input for each field
    if request.method == 'POST':
        deck_name = request.form.get('deck_name', '').strip()
        subject = request.form.get('subject', '').strip()
        description = request.form.get('description', '').strip()
        cover_color = request.form.get('cover_color', '').strip() or "#2E90E5"

        form_data.update({
            "deck_name": deck_name,
            "subject": subject,
            "description": description,
            "cover_color": cover_color,
        })

        if not deck_name or not subject:
            flash("Deck name and subject are required.")
            return render_template("create_deck.html", form_data=form_data)

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO topics (name, user_id, description, subject, cover_color)
            VALUES (?, ?, ?, ?, ?)
            """,
            (deck_name, session['user_id'], description or None, subject, cover_color)
        )
        
        # Modifies the database
        db.commit()

        # Notification for now
        flash(f"Deck '{deck_name}' created successfully.")
        return redirect(url_for('decks'))

    return render_template("create_deck.html", form_data=form_data)


@app.route("/delete_card/<int:card_id>", methods=["POST"])
def delete_card(card_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT topic_id FROM flashcards WHERE id = ?",
        (card_id,)
    )
    card = cursor.fetchone()

    if not card:
        flash("Card not found.")
        return redirect(url_for('decks'))

    deck_id = card[0]

    # Checking if this deck belongs to the specific user
    cursor.execute(
        "SELECT 1 FROM topics WHERE id = ? AND user_id = ?",
        (deck_id, session['user_id'])
    )

    # If the user tries to access someone else's card
    if not cursor.fetchone():
        flash("You do not have permission to delete that card.")
        return redirect(url_for('decks'))

    cursor.execute(
        "DELETE FROM flashcards WHERE id = ? AND topic_id = ?",
        (card_id, deck_id)
    )
    db.commit()

    # Next time you go to create a card, it will display this
    flash("Card deleted successfully.")

    return redirect(url_for('edit_deck', deck_id=deck_id))


@app.route('/edit_card/<int:card_id>', methods=['GET', 'POST'])
def edit_card(card_id):

    if 'username' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()

    # Get the card and make sure it belongs to this user
    # Since the flashcard table does not contain the user id, you can use join to get the corresponding user id from the topics table
    cursor.execute("""
        SELECT flashcards.id,
               flashcards.question,
               flashcards.answer,
               topics.id,
               topics.name
        FROM flashcards
        JOIN topics
            ON flashcards.topic_id = topics.id
        WHERE flashcards.id = ?
        AND topics.user_id = ?
    """, (card_id, session["user_id"]))

    card = cursor.fetchone()

    if not card:
        flash("Flashcard not found.")
        return redirect(url_for("decks"))

    form_data = {
        "question": card[1],
        "answer": card[2]
    }

    if request.method == "POST":

        question = request.form.get("question")
        answer = request.form.get("answer")

        if not question or not answer:
            flash("Question and answer are required.")
            return render_template(
                "add_card.html",
                deck={
                    "id": card[3],
                    "name": card[4]
                },
                form_data={"question": question, "answer": answer},
                edit_mode=True
            )

        cursor.execute("""
            UPDATE flashcards
            SET question=?,
                answer=?
            WHERE id=?
        """, (question, answer, card_id))

        db.commit()

        flash("Flashcard updated successfully.")

        return redirect(url_for(
            "edit_deck",
            deck_id=card[3]
        ))

    return render_template(
        "add_card.html",
        deck={
            "id": card[3],
            "name": card[4]
        },
        form_data=form_data,
        edit_mode=True
    )


@app.route('/update_deck/<int:deck_id>', methods=['GET', 'POST'])
def update_deck(deck_id):

    if 'username' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT id, name, description, subject, cover_color
        FROM topics
        WHERE id = ?
        AND user_id = ?
    """, (deck_id, session["user_id"]))

    deck = cursor.fetchone()

    if not deck:
        flash("Deck not found.")
        return redirect(url_for("decks"))

    form_data = {
        "deck_name": deck[1],
        "subject": deck[3],
        "description": deck[2] or "",
        "cover_color": deck[4] or "#2E90E5",
    }

    if request.method == "POST":

        deck_name = request.form.get("deck_name", "").strip()
        subject = request.form.get("subject", "").strip()
        description = request.form.get("description", "").strip()
        cover_color = request.form.get("cover_color")

        form_data.update({
            "deck_name": deck_name,
            "subject": subject,
            "description": description,
            "cover_color": cover_color,
        })

        if not deck_name or not subject:
            flash("Deck name and subject are required.")
            return render_template(
                "create_deck.html",
                form_data=form_data,
                edit_mode=True
            )

        # Update the data for the deck
        cursor.execute("""
            UPDATE topics
            SET name=?,
                subject=?,
                description=?,
                cover_color=?
            WHERE id=?
        """, (
            deck_name,
            subject,
            description or None,
            cover_color,
            deck_id
        ))

        db.commit()

        flash("Deck updated successfully.")
        return redirect(url_for("edit_deck", deck_id=deck_id))

    return render_template(
        "create_deck.html",
        form_data=form_data,
        edit_mode=True
    )


@app.route('/delete_deck/<int:deck_id>', methods=['POST'])
def delete_deck(deck_id):

    if 'username' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()

    # Because I have ON CASCADE DELETE in the database scheme for the flashcards table, all the flashcards that belong to the topic that is being deleted will be deleted
    cursor.execute(
        """
        DELETE FROM topics
        WHERE id = ?
        AND user_id = ?
        """,
        (deck_id, session["user_id"])
    )

    db.commit()

    flash("Deck deleted successfully.")
    return redirect(url_for("decks"))


@app.route('/study/<int:deck_id>', methods=['GET', 'POST'])
def study(deck_id):

    if 'username' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()

    # Check the deck belongs to the user
    cursor.execute("""
        SELECT id, name
        FROM topics
        WHERE id = ?
        AND user_id = ?
    """, (deck_id, session["user_id"]))

    deck = cursor.fetchone()

    if not deck:
        flash("Deck not found.")
        return redirect(url_for("decks"))

    # Get all flashcards for this deck
    cursor.execute("""
        SELECT id, question, answer
        FROM flashcards
        WHERE topic_id = ?
    """, (deck_id,))

    flashcards = cursor.fetchall()

    if len(flashcards) == 0:
        flash("This deck doesn't have any flashcards.")
        return redirect(url_for("edit_deck", deck_id=deck_id))

    # Start a new study session if there is not one already
    if session.get("study_session_deck") != deck_id:

        session["study_deck"] = deck_id
        session["cur_index"] = 0
        session["showing_answer"] = False

        cursor.execute("""
            INSERT INTO study_sessions
            (user_id, deck_id, cards_reviewed, started_at)
            VALUES (?, ?, 0, CURRENT_TIMESTAMP)
        """, (session["user_id"], deck_id))

        db.commit()

        # Get the sesion id and the deck that is currently being studied
        session["study_session_id"] = cursor.lastrowid
        session["study_session_deck"] = deck_id

    # Reset session when changing decks
    if session.get("study_deck") != deck_id:
        session["study_deck"] = deck_id
        session["cur_index"] = 0
        session["showing_answer"] = False

    if request.method == "POST":

        action = request.form.get("action")

        if action == "flip":
            session["showing_answer"] = not session["showing_answer"]

            if len(flashcards) == 1 and session.get("study_session_id") is not None:
                current_card_id = flashcards[session["cur_index"]]["id"]
                reviewed = session.get("reviewed_cards", [])

                if mark_reviewed_card(cursor, session, session["study_session_id"], current_card_id, reviewed):
                    db.commit()

        elif action == "next":

            if session["cur_index"] < len(flashcards) - 1:
                session["cur_index"] += 1

            session["showing_answer"] = False

            # Make sure user doesn't purposefully increase cards reviewed by spamming next and prev
            # This is done by keeping track of the card numbers of the cards that have been reviewed
            current_card_id = flashcards[session["cur_index"]]["id"]
            reviewed = session.get("reviewed_cards", [])

            # If the current card has not been reviewed then update the cards reviewed in the database
            if mark_reviewed_card(cursor, session, session["study_session_id"], current_card_id, reviewed):
                db.commit()

        elif action == "prev":

            if session["cur_index"] > 0:
                session["cur_index"] -= 1

            session["showing_answer"] = False

        elif action == "finish":

            if len(flashcards) == 1 and session.get("study_session_id") is not None:
                current_card_id = flashcards[session["cur_index"]]["id"]
                reviewed = session.get("reviewed_cards", [])

                if mark_reviewed_card(cursor, session, session["study_session_id"], current_card_id, reviewed):
                    db.commit()

            if session.get("study_session_id") is not None:            
                # Set completed = 1 and finish the study session
                cursor.execute("""
                    UPDATE study_sessions
                    SET ended_at = CURRENT_TIMESTAMP,
                        completed = 1
                    WHERE session_id = ?
                """, (session["study_session_id"],))

                db.commit()

            # Removing the old session info
            session.pop("study_session_id", None)
            session.pop("study_session_deck", None)
            session.pop("reviewed_cards", None)

            flash("Study session complete!")

            # Link to the finish button code in the JS by sending the JSON
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"redirect": url_for("decks")})

            return redirect(url_for("decks"))
        
    current_card = flashcards[session["cur_index"]]

    card_text = (
        current_card["answer"]
        if session["showing_answer"]
        else current_card["question"]
    )

    # Check if data is needed for JS (xmlhttp REQUEST)
    # Then return the json containing the needed data
    # This is done instead of changing pages to ensure smooth experience
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "card_text": card_text,
            "current_index": session["cur_index"],
            "total_cards": len(flashcards)
        })

    return render_template(
        "study.html",
        deck_id=deck_id,
        deck_name=deck["name"],
        card_text=card_text,
        current_index=session["cur_index"],
        total_cards=len(flashcards)
    )


@app.route('/progress')
def progress():
    if 'username' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()

    # Need to execute queries to get progress stats

    # Number of decks
    cursor.execute("""
        SELECT COUNT(*)
        FROM topics
        WHERE user_id = ?
    """, (session['user_id'],))
    deck_count = cursor.fetchone()[0]

    # Number of flashcards
    # Join ensures there is a match between the flashcards id and the topic id
    cursor.execute("""
        SELECT COUNT(*)
        FROM flashcards
        JOIN topics ON flashcards.topic_id = topics.id
        WHERE topics.user_id = ?
    """, (session['user_id'],))
    flashcard_count = cursor.fetchone()[0]

    # Number of reviews
    # Coalesce ensures that no null is received as a result and if so, zero is given as the output
    cursor.execute("""
        SELECT COALESCE(SUM(cards_reviewed), 0)
        FROM study_sessions
        WHERE user_id = ? AND completed = 1
    """, (session['user_id'],))
    reviews = cursor.fetchone()[0]

    # Number of study sessions
    cursor.execute("""
        SELECT COUNT(*)
        FROM study_sessions
        WHERE user_id = ?
    """, (session['user_id'],))
    study_sessions = cursor.fetchone()[0]

    # The study dates
    cursor.execute("""
        SELECT DISTINCT DATE(started_at) AS study_day
        FROM study_sessions
        WHERE user_id = ?
        ORDER BY study_day
    """, (session['user_id'],))

    # Process the data into datetime format
    study_dates = [datetime.strptime(row[0], "%Y-%m-%d").date() for row in cursor.fetchall()]

    # Get the latest time the user studied
    cursor.execute("""
        SELECT started_at
        FROM study_sessions
        WHERE user_id = ?
        ORDER BY started_at DESC
        LIMIT 1
    """, (session['user_id'],))

    # Get JUST the latest time the user studied
    last_study_row = cursor.fetchone()
    last_studied = format_study_time(last_study_row[0]) if last_study_row and last_study_row[0] else "No study sessions yet"

    # Finds the deck which the user has reviewed the most
    # 3 most studied decks
    cursor.execute("""
        SELECT topics.name, COALESCE(SUM(study_sessions.cards_reviewed), 0) AS review_count
        FROM study_sessions
        JOIN topics ON study_sessions.deck_id = topics.id
        WHERE study_sessions.user_id = ?
        GROUP BY topics.id, topics.name
        ORDER BY review_count DESC, topics.name ASC
        LIMIT 3
    """, (session['user_id'],))

    # Format the data
    top_decks = [
        {"name": row[0], "reviews": row[1]}
        for row in cursor.fetchall()
    ]

    # Get the recent sessions
    cursor.execute("""
        SELECT study_sessions.started_at, topics.name, study_sessions.cards_reviewed
        FROM study_sessions
        JOIN topics ON study_sessions.deck_id = topics.id
        WHERE study_sessions.user_id = ?
        ORDER BY study_sessions.started_at DESC
        LIMIT 3
    """, (session['user_id'],))

    # Format the data
    recent_sessions = [
        {
            "date_label": format_recent_label(row[0]),
            "deck_name": row[1],
            "cards_reviewed": row[2] or 0
        }
        for row in cursor.fetchall()
    ]

    return render_template(
        "progress.html",
        deck_count=deck_count,
        flashcard_count=flashcard_count,
        reviews=reviews,
        study_sessions=study_sessions,
        streak=calculate_streak(study_dates),
        longest_streak=calculate_longest_streak(study_dates),
        last_studied=last_studied,
        top_decks=top_decks,
        recent_sessions=recent_sessions,
    )


@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()

    # Get the user's email
    cursor.execute("""
        SELECT email
        FROM users
        WHERE id = ?
    """, (session['user_id'],))
    user_row = cursor.fetchone()
    email = user_row['email'] if user_row else "No email available"

    # Get the number of decks
    cursor.execute("""
        SELECT COUNT(*)
        FROM topics
        WHERE user_id = ?
    """, (session['user_id'],))
    deck_count = cursor.fetchone()[0]

    # Get the number of flashcards
    cursor.execute("""
        SELECT COUNT(*)
        FROM flashcards
        JOIN topics ON flashcards.topic_id = topics.id
        WHERE topics.user_id = ?
    """, (session['user_id'],))
    flashcard_count = cursor.fetchone()[0]

    # Get the current streak
    cursor.execute("""
        SELECT DISTINCT DATE(started_at) AS study_day
        FROM study_sessions
        WHERE user_id = ?
        ORDER BY study_day
    """, (session['user_id'],))
    study_dates = [datetime.strptime(row[0], "%Y-%m-%d").date() for row in cursor.fetchall()]
    streak = calculate_streak(study_dates)

    return render_template(
        "profile.html",
        username=session['username'],
        email=email,
        deck_count=deck_count,
        flashcard_count=flashcard_count,
        streak=streak,
    )


@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # Delete the user's data
    cursor.execute("DELETE FROM study_sessions WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM flashcards WHERE topic_id IN (SELECT id FROM topics WHERE user_id = ?)", (user_id,))
    cursor.execute("DELETE FROM topics WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()

    session.clear()
    flash("Your account has been deleted.")
    return redirect(url_for('home'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.errorhandler(404)
def page_not_found(error):
    return render_template("errors/404.html"), 404

if __name__ == "__main__":
    app.run(debug=True)