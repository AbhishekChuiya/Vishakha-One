
import os
import sqlite3
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db.sqlite3")

if not os.path.exists(DB_PATH):
    raise FileNotFoundError("db.sqlite3 not found!")

# Create a fresh backup
backup_name = (
    "db_backup_" +
    datetime.now().strftime("%Y%m%d_%H%M%S") +
    ".sqlite3"
)

backup_path = os.path.join(BASE_DIR, backup_name)
shutil.copy2(DB_PATH, backup_path)

print("Backup created:", backup_path)

connection = sqlite3.connect(DB_PATH)

try:
    cursor = connection.cursor()

    cursor.execute(
        "PRAGMA table_info(portal_companyapplication)"
    )

    columns = [row[1] for row in cursor.fetchall()]

    print("Existing columns:", columns)

    if "icon_path" not in columns:
        cursor.execute("""
            ALTER TABLE portal_companyapplication
            ADD COLUMN icon_path
            varchar(255) NOT NULL DEFAULT ''
        """)

        print("SUCCESS: icon_path column added.")

        # Preserve the existing icon values
        if "icon" in columns:
            cursor.execute("""
                UPDATE portal_companyapplication
                SET icon_path = icon
                WHERE icon IS NOT NULL
                  AND icon != ''
            """)

            print("Existing icon values copied.")

    else:
        print("icon_path already exists.")

    connection.commit()

    cursor.execute(
        "PRAGMA table_info(portal_companyapplication)"
    )

    updated_columns = [
        row[1] for row in cursor.fetchall()
    ]

    print("Updated columns:", updated_columns)

finally:
    connection.close()

print("Database repair completed.")
