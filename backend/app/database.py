import psycopg2
import os
from app.config import settings

def init_db():
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diagnosis_history (
                id SERIAL PRIMARY KEY,
                image_path TEXT NOT NULL,
                predicted_disease TEXT NOT NULL,
                confidence REAL NOT NULL,
                user_feedback_disease TEXT,
                is_verified INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print("PostgreSQL Database initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize PostgreSQL: {e}")
    
def save_diagnosis(image_path: str, predicted: str, confidence: float):
    conn = psycopg2.connect(settings.DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO diagnosis_history (image_path, predicted_disease, confidence)
        VALUES (%s, %s, %s) RETURNING id
    ''', (image_path, predicted, confidence))
    record_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return record_id