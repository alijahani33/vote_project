import sqlite3

# Updated Database URL
DATABASE_URL = "voting_system.db"

def create_connection():
    """
    Create a connection to the SQLite database.
    """
    conn = sqlite3.connect(DATABASE_URL)
    return conn

def create_tables():
    """
    Create the necessary tables: voters, candidates, votes.
    Note: 'national_code' has been replaced with 'phone_number'.
    """
    conn = create_connection()
    cursor = conn.cursor()

    # Updated Voters table without 'national_code'
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

    conn.commit()
    conn.close()

def add_voter(phone_number, first_name, last_name):
    """
    Add a new voter to the 'voters' table.
    Replaces 'national_code' with 'phone_number'.
    """
    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
        INSERT INTO voters (phone_number, first_name, last_name)
        VALUES (?, ?, ?)
        ''', (phone_number, first_name, last_name))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:  # Prevent duplicate phone numbers
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

    cursor.execute('SELECT * FROM candidates')
    candidates = cursor.fetchall()

    conn.close()
    return candidates

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

def count_votes(voter_id):
    """
    Count the number of votes cast by a specific voter.
    """
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM votes WHERE voter_id = ?', (voter_id,))
    count = cursor.fetchone()[0]

    conn.close()
    return count

def get_voter_by_phone_number(phone_number):
    """
    Retrieve a voter's ID based on their phone number.
    """
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM voters WHERE phone_number = ?", (phone_number,))
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
    GROUP BY candidates.name
    ''')

    results = cursor.fetchall()
    conn.close()
    return results

def populate_database():
    """
    Populate the database with sample candidates and voters.
    Note: 'national_code' has been replaced with 'phone_number' in voters.
    """
    # Sample Candidates
    candidates = ["علی رضایی", "حسین حسینی", "محمد محمدی"]
    for candidate_name in candidates:
        candidate_id = add_candidate(candidate_name)
        print(f"کاندید {candidate_name} با شناسه {candidate_id} اضافه شد.")

    # Sample Voters (Using phone numbers instead of national codes)
    voters = [
        ("09137901844", "رضا", "احمدی"),
        ("09387275159", "سارا", "باقری"),
        ("09170535098", "حسن", "کریمی"),
        ("09175367505", "مریم", "حیدری"),
        ("09173825941", "تستی", "تستی"),  # Test for duplicate phone number
        ("09177767440", "یک", "دو"),
        ("09179244093", "یک", "دو")  # Test for duplicate phone number
    ]
    for phone_number, first_name, last_name in voters:
        voter_id = add_voter(phone_number, first_name, last_name)
        if voter_id:  # Only print if voter was successfully added
            print(f"رای‌دهنده با شماره تلفن {phone_number} و شناسه {voter_id} اضافه شد.")

if __name__ == "__main__":
    create_tables()
    populate_database()

    # Display candidates and voters
    print("\nلیست کاندیداها:")
    for candidate in get_candidates():
        print(candidate)

    print("\nلیست رای دهندگان:")
    for voter in get_voters():
        print(voter)

    print("\nشمارش آرا:")
    for name, count in get_vote_counts():
        print(f"{name}: {count} رای")
