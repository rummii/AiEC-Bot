import sqlite3
import os

# Dynamically checks if running on your specific cPanel environment; falls back to local root for Codespaces
CPANEL_PATH = "/home/vsmwrurd/repositories/AiEC-Bot/aiec_bot.db"
DB_PATH = CPANEL_PATH if os.path.exists("/home/vsmwrurd") else "aiec_bot.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE,
            username TEXT,
            role TEXT DEFAULT 'client',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Conversations Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            status TEXT DEFAULT 'active',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        """)

        # 3. Tracking Logs (Telemetry metrics)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracking_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            interaction_type TEXT CHECK(interaction_type IN ('text', 'voice')),
            raw_input TEXT,
            bot_response TEXT,
            audio_duration_secs REAL DEFAULT 0.0,
            confidence_score REAL,
            file_path TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES conversations(session_id) ON DELETE CASCADE
        );
        """)

        # 4. Knowledge Base Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_base (
            kb_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            keyword TEXT,
            content TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_session ON tracking_logs(session_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id);")
        conn.commit()

init_db()
