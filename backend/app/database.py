import psycopg2
from app.config import settings


def _connect():
    return psycopg2.connect(settings.DATABASE_URL)


def init_db():
    """Initializes the PostgreSQL database."""
    try:
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
