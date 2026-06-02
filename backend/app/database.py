import psycopg2
from psycopg2 import sql
from app.config import settings
from urllib.parse import urlparse, unquote


def _parse_database_url():
    parsed = urlparse(settings.DATABASE_URL)
    if not parsed.path or parsed.path == "/":
        raise ValueError("DATABASE_URL must include a database name.")

    return {
        "dbname": parsed.path.lstrip("/"),
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
    }


def _ensure_database_exists():
    db_config = _parse_database_url()
    admin_config = dict(db_config)
    admin_config["dbname"] = "postgres"

    conn = psycopg2.connect(**admin_config)
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_config["dbname"],))
    exists = cursor.fetchone() is not None

    if not exists:
        cursor.execute(sql.SQL("CREATE DATABASE {} ").format(sql.Identifier(db_config["dbname"])))
        print(f"Created PostgreSQL database '{db_config['dbname']}'.")

    cursor.close()
    conn.close()


def _connect():
    return psycopg2.connect(settings.DATABASE_URL)


def init_db():
    """Initializes the PostgreSQL database."""
    try:
        _ensure_database_exists()

        conn   = _connect()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diagnosis_history (
                id                    SERIAL PRIMARY KEY,
                image_path            TEXT NOT NULL,
                predicted_disease     TEXT NOT NULL,
                confidence            REAL NOT NULL,
                user_feedback_disease TEXT,
                is_verified           INTEGER DEFAULT 0,
                timestamp             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print("PostgreSQL Database initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize PostgreSQL: {e}")


def save_diagnosis(image_path: str, predicted: str, confidence: float) -> int:
    conn   = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO diagnosis_history (image_path, predicted_disease, confidence) "
        "VALUES (%s, %s, %s) RETURNING id",
        (image_path, predicted, confidence)
    )
    record_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return record_id


def update_feedback(record_id: int, actual_disease: str):
    conn   = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE diagnosis_history SET user_feedback_disease = %s, is_verified = 1 WHERE id = %s",
        (actual_disease, record_id)
    )
    conn.commit()
    conn.close()


# ✅ NEW: helper used by routes.py to get image path without inline DB calls
def get_image_path(record_id: int):
    try:
        conn   = _connect()
        cursor = conn.cursor()
        cursor.execute("SELECT image_path FROM diagnosis_history WHERE id = %s", (record_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None
