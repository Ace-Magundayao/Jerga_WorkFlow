"""Adds the face/ID columns to the users table for existing databases.
Run once with:  python migrate_user_biometrics.py
"""
import sqlite3

conn = sqlite3.connect("workflow.db")
cursor = conn.cursor()

# Columns already present in the users table
existing = {row[1] for row in cursor.execute("PRAGMA table_info(users)").fetchall()}

columns = [
    ("face_encoding", "TEXT"),
    ("face_enrolled_at", "DATETIME"),
    ("face_photo", "VARCHAR(255)"),
    ("id_document", "VARCHAR(255)"),
    ("id_document_type", "VARCHAR(50)"),
    ("id_verified", "BOOLEAN DEFAULT 0 NOT NULL"),
    ("id_verified_by_id", "INTEGER"),
]

# Add only the columns that are missing
for name, coltype in columns:
    if name not in existing:
        cursor.execute(f"ALTER TABLE users ADD COLUMN {name} {coltype}")
        print("Added column:", name)

conn.commit()
conn.close()
print("Migration complete.")
