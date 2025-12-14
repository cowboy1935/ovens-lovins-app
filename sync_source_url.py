import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "recipes.db"
JSON_PATH = BASE_DIR / "recipes.json"  # << your file name


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def main():
    conn = get_conn()
    cur = conn.cursor()

    # Add source_url column if it doesn't exist yet
    try:
        cur.execute("ALTER TABLE recipes ADD COLUMN source_url TEXT")
    except sqlite3.OperationalError:
        # Column already exists, ignore
        pass

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    updated = 0

    for r in recipes:
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()

        if not title or not url:
            continue

        cur.execute(
            "UPDATE recipes SET source_url = ? WHERE lower(title) = lower(?)",
            (url, title.lower()),
        )
        if cur.rowcount:
            updated += 1

    conn.commit()
    conn.close()

    print(f"Updated source_url for {updated} recipes.")


if __name__ == "__main__":
    main()
