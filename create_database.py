import sqlite3

conn = sqlite3.connect("event_tickets.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS Events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date TEXT,
    location TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Attendees (
    attendee_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Tickets (
    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    attendee_id INTEGER,
    event_id INTEGER,
    ticket_type TEXT CHECK(ticket_type IN ('WVIP', 'VIP', 'Normal', 'Staff')) NOT NULL,
    barcode TEXT UNIQUE NOT NULL,
    pass_design TEXT,
    FOREIGN KEY(attendee_id) REFERENCES Attendees(attendee_id),
    FOREIGN KEY(event_id) REFERENCES Events(event_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

conn.commit()
conn.close()

print("Database and tables created successfully.")