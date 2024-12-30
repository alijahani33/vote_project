import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from collections import OrderedDict

DATABASE_URL = "voting_system.db"

app = Flask(__name__)

def create_connection():
    conn = sqlite3.connect(DATABASE_URL)
    return conn

def create_tables():
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS voters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        national_code TEXT UNIQUE NOT NULL,
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


import random
import datetime

# Function to generate OTP and store it in the database
def generate_otp(phone_number):
    otp = str(random.randint(100000, 999999))  # Generate 6-digit OTP
    expiration_time = datetime.datetime.now() + datetime.timedelta(minutes=5)  # OTP expires in 5 minutes

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

# Function to verify OTP
def verify_otp(phone_number, entered_otp):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT otp, expiration_time FROM otp_verification WHERE phone_number = ?
    ''', (phone_number,))
    record = cursor.fetchone()

    conn.close()

    if not record:
        return False  # No OTP found for this phone number

    otp, expiration_time = record
    if entered_otp == otp and datetime.datetime.now() < datetime.datetime.fromisoformat(expiration_time):
        return True

    return False



def add_voter(national_code, first_name, last_name):
    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
        INSERT INTO voters (national_code, first_name, last_name)
        VALUES (?, ?, ?)
        ''', (national_code, first_name, last_name))
        voter_id = cursor.lastrowid
        conn.commit()
        return voter_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def add_candidate(name):
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
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id, name FROM candidates')
    candidates = cursor.fetchall()

    conn.close()
    return candidates

def count_votes(voter_id):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM votes WHERE voter_id = ?', (voter_id,))
    count = cursor.fetchone()[0]

    conn.close()
    return count

def get_voter_by_national_code(national_code):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM voters WHERE national_code = ?", (national_code,))
    voter = cursor.fetchone()

    conn.close()
    return voter

def get_vote_counts():
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
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM votes")
    total_votes = cursor.fetchone()[0]
    conn.close()
    return total_votes

def cast_vote(voter_id, candidate_id):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO votes (voter_id, candidate_id)
    VALUES (?, ?)
    ''', (voter_id, candidate_id))

    conn.commit()
    conn.close()

@app.route("/", methods=['GET', 'POST'])
def index():
    create_tables()
    candidates = get_candidates()
    return render_template('index.html', candidates=candidates)

@app.route("/vote", methods=['POST'])
def vote():
    national_code = request.form.get('national_code')
    candidate_ids = request.form.getlist('candidate_ids')

    if not national_code:
        return render_template('index.html', candidates=get_candidates(), error_message="لطفا کد ملی خود را وارد کنید.")

    voter = get_voter_by_national_code(national_code)
    if not voter:
        return render_template('index.html', candidates=get_candidates(), error_message="کاربری با این کد ملی یافت نشد.")

    voter_id = voter[0]

    if count_votes(voter_id) >= 2:
        return render_template('index.html', candidates=get_candidates(), error_message="شما قبلا رای داده‌اید.")

    if not candidate_ids:
        return render_template('index.html', candidates=get_candidates(), error_message="لطفا حداقل یک نامزد را انتخاب کنید.")

    if len(candidate_ids) > 2:
        return render_template('index.html', candidates=get_candidates(), error_message="شما حداکثر می‌توانید به دو نامزد رای دهید.")

    for candidate_id in candidate_ids:
        cast_vote(voter_id, candidate_id)

    return render_template('index.html', candidates=get_candidates(), success_message="رای شما با موفقیت ثبت شد.")

@app.route("/results")
def results():
    vote_counts = get_vote_counts()
    total_votes = get_total_votes()
    return render_template('results.html', vote_counts=vote_counts, total_votes=total_votes)


@app.route("/otp", methods=["GET", "POST"])
def otp_page():
    if request.method == "POST":
        phone_number = request.form.get("phone_number")
        if not phone_number:
            return render_template("otp.html", error_message="Please enter your phone number.")

        # Generate OTP and send it
        otp = generate_otp(phone_number)
        print(f"Generated OTP for {phone_number}: {otp}")  # For testing; remove in production

        return render_template("verify_otp.html", phone_number=phone_number)

    return render_template("otp.html")

@app.route("/verify_otp", methods=["POST"])
def verify_otp_page():
    phone_number = request.form.get("phone_number")
    entered_otp = request.form.get("otp")

    if verify_otp(phone_number, entered_otp):
        return render_template("success.html", message="Phone number verified successfully!")
    else:
        return render_template("verify_otp.html", phone_number=phone_number, error_message="Invalid or expired OTP.")



if __name__ == "__main__":
    with app.app_context():
        create_tables()
        if not get_candidates():
            add_candidate("نامزد شماره ۱")
            add_candidate("نامزد شماره ۲")
            add_candidate("نامزد شماره ۳")
            add_candidate("نامزد شماره ۴")
    app.run(debug=True)
