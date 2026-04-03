import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "users.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            risk_score INTEGER DEFAULT 0,
            total_flags INTEGER DEFAULT 0,
            last_updated TIMESTAMP,
            grooming_stage_max TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            user_id TEXT,
            risk_level TEXT,
            confidence REAL,
            timestamp TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT user_id, risk_score, total_flags, last_updated, grooming_stage_max FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    if not row:
        now = datetime.datetime.now().isoformat()
        c.execute('INSERT INTO users (user_id, risk_score, total_flags, last_updated, grooming_stage_max) VALUES (?, ?, ?, ?, ?)',
                  (user_id, 0, 0, now, "Normal"))
        conn.commit()
        row = (user_id, 0, 0, now, "Normal")
    conn.close()
    return {
        "user_id": row[0],
        "risk_score": row[1],
        "total_flags": row[2],
        "last_updated": row[3],
        "grooming_stage_max": row[4]
    }

def update_user_risk(user_id, risk_level):
    conn = get_connection()
    c = conn.cursor()
    score_increment = 0
    flag_increment = 0

    if risk_level == 'warning':
        score_increment = 1
        flag_increment = 1
    elif risk_level == 'hazardous':
        score_increment = 3
        flag_increment = 1

    now = datetime.datetime.now().isoformat()
    c.execute('''
        UPDATE users 
        SET risk_score = risk_score + ?, 
            total_flags = total_flags + ?, 
            last_updated = ? 
        WHERE user_id = ?
    ''', (score_increment, flag_increment, now, user_id))
    conn.commit()
    conn.close()

def log_interaction(conversation_id, user_id, risk_level, confidence):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.datetime.now().isoformat()
    c.execute('''
        INSERT INTO interactions (conversation_id, user_id, risk_level, confidence, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (conversation_id, user_id, risk_level, confidence, now))
    conn.commit()
    conn.close()

def get_user_interaction_stats(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*), COUNT(DISTINCT conversation_id) FROM interactions WHERE user_id = ?', (user_id,))
    total_inter, unique_convos = c.fetchone()
    
    c.execute('SELECT COUNT(*) FROM interactions WHERE user_id = ? AND risk_level = "hazardous"', (user_id,))
    total_hazardous = c.fetchone()[0]
    conn.close()
    
    return {
        "total_interactions": total_inter or 0,
        "total_hazardous": total_hazardous or 0,
        "unique_conversations": unique_convos or 0
    }
