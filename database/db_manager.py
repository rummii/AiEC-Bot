import os
import sqlite3

# Database backend selection: 'sqlite' for local development, 'postgres' for Google Cloud / Cloud SQL
DB_TYPE = os.getenv("DB_TYPE", "sqlite").strip().lower()

# SQLite fallback path (local development)
CPANEL_PATH = "/home/vsmwrurd/repositories/AiEC-Bot/aiec_bot.db"
DB_PATH = CPANEL_PATH if os.path.exists("/home/vsmwrurd") else "aiec_bot.db"


def get_connection():
    """Create and return a database connection.

    Supports both SQLite (local) and PostgreSQL (Cloud SQL on Google Cloud).
    """
    if DB_TYPE == "postgres":
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError as exc:
            raise RuntimeError(
                "DB_TYPE is 'postgres' but 'psycopg2' is not installed. "
                "Run: pip install psycopg2-binary"
            ) from exc

        required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASS"]
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise RuntimeError(
                "Missing required PostgreSQL environment variables: "
                + ", ".join(missing)
            )

        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
        )
        conn.autocommit = False
        # RealDictCursor provides dict-like row access (same as sqlite3.Row)
        conn.cursor_factory = RealDictCursor
        return conn

    # SQLite fallback for local development
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_param_placeholder():
    """Return the correct parameter placeholder for the current DB backend."""
    return "%s" if DB_TYPE == "postgres" else "?"


def init_db():
    """Initialize the database schema for the configured backend."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Users Table
        pk_type = "SERIAL" if DB_TYPE == "postgres" else "INTEGER PRIMARY KEY AUTOINCREMENT"
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS users (
                user_id {pk_type},
                telegram_id TEXT UNIQUE,
                username TEXT,
                role TEXT DEFAULT 'client',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 2. Conversations Table
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS conversations (
                session_id {pk_type},
                user_id INTEGER,
                status TEXT DEFAULT 'active',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            """
        )

        # 3. Tracking Logs (Telemetry metrics)
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS tracking_logs (
                log_id {pk_type},
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
            """
        )

        # 4. Knowledge Base Table
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                kb_id {pk_type},
                category TEXT,
                keyword TEXT,
                content TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_session ON tracking_logs(session_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id);")
        conn.commit()


init_db()
