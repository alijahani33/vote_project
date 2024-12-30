import sqlite3
import random
import datetime
from collections import OrderedDict
from flask import Flask, render_template, request, redirect, url_for, session, flash

# Configuration
DATABASE_URL = "voting_system.db"
SECRET_KEY = 'smiletothelife'  # Change this to a strong random key in production
OTP_EXPIRATION_MINUTES = 5
MAX_VOTES_PER_VOTER = 2  # Adjust as needed

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

# Database Utilities
def create_connection():
    """
    Create a connection to the SQLite database.
    """
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    return conn

def create_tables():
    """
    Create the necessary tables: voters, candidates, votes, otp_verification.
    """
    conn = create_connection()
    cursor = conn.cursor()

    # Voters table with phone_number instead of national_code
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS voters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT UNIQUE NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id INTEGER NOT NULL,
        candidate_id INTEGER NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (voter_id) REFERENCES voters (id),
        FOREIGN KEY (candidate_id) REFERENCES candidates (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS otp_verification (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT UNIQUE NOT NULL,
        otp TEXT NOT NULL,
        expiration_time DATETIME NOT NULL
    )
    ''')

    conn.commit()
    conn.close()

# OTP Utilities
def generate_otp(phone_number):
    """
    Generate a 6-digit OTP, store it in the database with an expiration time, and return the OTP.
    """
    otp = str(random.randint(100000, 999999))  # Generate 6-digit OTP
    expiration_time = datetime.datetime.now() + datetime.timedelta(minutes=OTP_EXPIRATION_MINUTES)

    conn = create_connection()
    cursor = conn.cursor()

    # Insert or update OTP for the phone number
    cursor.execute('''
    INSERT INTO otp_verification (phone_number, otp, expiration_time)
    VALUES (?, ?, ?)
    ON CONFLICT(phone_number) DO UPDATE SET otp = excluded.otp, expiration_time = excluded.expiration_time
    ''', (phone_number, otp, expiration_time))

    conn.commit()
    conn.close()
    return otp


def get_voters():
    """
    Retrieve all voters from the 'voters' table.
    """
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM voters')
    voters = cursor.fetchall()

    conn.close()
    return voters

def verify_otp_db(phone_number, entered_otp):
    """
    Verify the entered OTP against the stored OTP for the given phone number.
    """
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT otp, expiration_time FROM otp_verification WHERE phone_number = ?
    ''', (phone_number,))
    record = cursor.fetchone()

    conn.close()

    if not record:
        return False  # No OTP found for this phone number

    otp, expiration_time = record['otp'], record['expiration_time']
    expiration_time = datetime.datetime.fromisoformat(expiration_time)
    if entered_otp == otp and datetime.datetime.now() < expiration_time:
        return True

    return False

# Voter and Candidate Utilities
def add_voter(phone_number, first_name, last_name):
    """
    Add a new voter to the 'voters' table.
    """
    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
        INSERT INTO voters (phone_number, first_name, last_name)
        VALUES (?, ?, ?)
        ''', (phone_number, first_name, last_name))
        voter_id = cursor.lastrowid
        conn.commit()
        return voter_id
    except sqlite3.IntegrityError:
        print(f"خطا: رای دهنده با شماره تلفن {phone_number} قبلا ثبت شده است.")
        return None
    finally:
        conn.close()

def add_candidate(name):
    """
    Add a new candidate to the 'candidates' table.
    """
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO candidates (name)
    VALUES (?)
    ''', (name,))

    candidate_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return candidate_id

def get_candidates():
    """
    Retrieve all candidates from the 'candidates' table.
    """
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id, name FROM candidates')
    candidates = cursor.fetchall()

    conn.close()
    return candidates

def count_votes(voter_id):
    """
    Count the number of votes cast by a specific voter.
    """
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as count FROM votes WHERE voter_id = ?', (voter_id,))
    count = cursor.fetchone()['count']

    conn.close()
    return count

def get_voter_by_phone_number(phone_number):
    """
    Retrieve a voter's details based on their phone number.
    """
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM voters WHERE phone_number = ?", (phone_number,))
    voter = cursor.fetchone()

    conn.close()
    return voter

def get_vote_counts():
    """
    Retrieve the number of votes each candidate has received.
    """
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT candidates.name, COUNT(votes.candidate_id) AS vote_count
    FROM candidates
    LEFT JOIN votes ON candidates.id = votes.candidate_id
    GROUP BY candidates.id, candidates.name
    ORDER BY vote_count DESC
    ''')

    results = OrderedDict(cursor.fetchall())
    conn.close()
    return results

def get_total_votes():
    """
    Retrieve the total number of votes cast.
    """
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM votes")
    total_votes = cursor.fetchone()['total']
    conn.close()
    return total_votes

def cast_vote(voter_id, candidate_id):
    """
    Cast a vote for a candidate by a voter.
    """
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO votes (voter_id, candidate_id)
    VALUES (?, ?)
    ''', (voter_id, candidate_id))

    conn.commit()
    conn.close()

# Initialize Database and Perform Migration
def initialize_database():
    """
    Initialize the database by creating tables.
    """
    create_tables()
    # Uncomment the following line **only once** to perform the migration
    # migrate_voters_table()

initialize_database()

# Migration Function (Run Once)
def migrate_voters_table():
    """
    Migrate the 'voters' table by replacing 'national_code' with 'phone_number'.
    """
    conn = create_connection()
    cursor = conn.cursor()

    # Check if migration has already been done
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='voters_new'")
    if cursor.fetchone():
        print("Migration already performed.")
        conn.close()
        return

    # Create new voters table without national_code
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS voters_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT UNIQUE NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL
    )
    ''')

    # Transfer data from national_code to phone_number
    cursor.execute('''
    INSERT INTO voters_new (phone_number, first_name, last_name)
    SELECT national_code, first_name, last_name FROM voters
    ''')

    # Drop old voters table
    cursor.execute('DROP TABLE voters')

    # Rename voters_new to voters
    cursor.execute('ALTER TABLE voters_new RENAME TO voters')

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

# Routes
@app.route("/", methods=['GET', 'POST'])
def otp_page():
    """
    Handle OTP generation and sending.
    """
    if request.method == "POST":
        phone_number = request.form.get("phone_number")
        if not phone_number:
            flash("لطفاً شماره تلفن خود را وارد کنید.", "danger")
            return render_template("otp.html")

        # Check if phone number exists
        voter = get_voter_by_phone_number(phone_number)
        if not voter:
            flash("شماره تلفن یافت نشد. لطفاً ابتدا ثبت‌نام کنید.", "danger")
            return render_template("otp.html")

        # Generate OTP and send it
        otp = generate_otp(phone_number)
        print(f"Generated OTP for {phone_number}: {otp}")  # Replace with actual SMS sending in production

        session['phone_number'] = phone_number  # Store phone number in session for verification
        flash("کد تایید به شماره تلفن شما ارسال شد.", "success")
        return redirect(url_for("verify_otp_page"))

    return render_template("otp.html")

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp_page():
    """
    Handle OTP verification.
    """
    phone_number = session.get('phone_number')
    if not phone_number:
        flash("جلسه منقضی شده یا دسترسی نامعتبر. لطفاً دوباره تلاش کنید.", "danger")
        return redirect(url_for("otp_page"))

    if request.method == "POST":
        entered_otp = request.form.get("otp")
        if not entered_otp:
            flash("لطفاً کد تایید را وارد کنید.", "danger")
            return render_template("verify_otp.html", phone_number=phone_number)

        if verify_otp_db(phone_number, entered_otp):
            voter = get_voter_by_phone_number(phone_number)
            session['voter_id'] = voter['id']
            session.pop('phone_number', None)  # Remove phone_number from session
            flash("شماره تلفن با موفقیت تایید شد!", "success")
            return redirect(url_for("vote_page"))
        else:
            flash("کد تایید نامعتبر یا منقضی شده است. لطفاً دوباره تلاش کنید.", "danger")
            return render_template("verify_otp.html", phone_number=phone_number)

    return render_template("verify_otp.html", phone_number=phone_number)

@app.route("/vote", methods=['GET', 'POST'])
def vote_page():
    """
    Handle the voting process.
    """
    voter_id = session.get('voter_id')
    if not voter_id:
        flash("شما باید ابتدا شماره تلفن خود را تایید کنید.", "danger")
        return redirect(url_for("otp_page"))

    voters = get_voters()
    voter = None
    for v in voters:
        if v['id'] == voter_id:
            voter = v
            break

    if not voter:
        flash("رای دهنده یافت نشد. لطفاً دوباره تلاش کنید.", "danger")
        return redirect(url_for("otp_page"))

    candidates = get_candidates()

    if request.method == 'POST':
        candidate_ids = request.form.getlist('candidate_ids')

        if not candidate_ids:
            flash("لطفاً حداقل یک نامزد را انتخاب کنید.", "danger")
            return render_template('index.html', candidates=candidates)

        if len(candidate_ids) > MAX_VOTES_PER_VOTER:
            flash(f"شما حداکثر می‌توانید به {MAX_VOTES_PER_VOTER} نامزد رای دهید.", "danger")
            return render_template('index.html', candidates=candidates)

        current_vote_count = count_votes(voter_id)
        if current_vote_count + len(candidate_ids) > MAX_VOTES_PER_VOTER:
            allowed_votes = MAX_VOTES_PER_VOTER - current_vote_count
            flash(f"شما می‌توانید فقط {allowed_votes} رای دیگر ثبت کنید.", "danger")
            return render_template('index.html', candidates=candidates)

        for candidate_id in candidate_ids:
            cast_vote(voter_id, candidate_id)

        # Retrieve voter's first and last name for the confirmation message
        first_name = voter['first_name']
        last_name = voter['last_name']

        flash(f"آقای {first_name} {last_name}, رای شما با موفقیت ثبت شد.", "success")
        return render_template("vote_confirmation.html", first_name=first_name, last_name=last_name)

    return render_template('index.html', candidates=candidates)

@app.route("/results")
def results_page():
    """
    Display the election results.
    """
    vote_counts = get_vote_counts()
    total_votes = get_total_votes()
    return render_template('results.html', vote_counts=vote_counts, total_votes=total_votes)

@app.route("/logout")
def logout():
    """
    Handle user logout by clearing the session.
    """
    session.clear()
    flash("شما از سیستم خارج شدید.", "info")
    return redirect(url_for("otp_page"))

# Utility route to register a new voter (optional)
@app.route("/register", methods=['GET', 'POST'])
def register_page():
    """
    Handle voter registration.
    """
    if request.method == "POST":
        phone_number = request.form.get("phone_number")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")

        if not all([phone_number, first_name, last_name]):
            flash("تمامی فیلدها الزامی هستند.", "danger")
            return render_template("register.html")

        voter_id = add_voter(phone_number, first_name, last_name)
        if voter_id:
            flash("ثبت‌نام با موفقیت انجام شد! اکنون می‌توانید وارد شوید.", "success")
            return redirect(url_for("otp_page"))
        else:
            flash("ثبت‌نام ناموفق. ممکن است شماره تلفن قبلاً وجود داشته باشد.", "danger")
            return render_template("register.html")

    return render_template("register.html")

# Run the app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)
