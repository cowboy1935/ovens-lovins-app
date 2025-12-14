import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "recipes.db"
JSON_PATH = BASE_DIR / "recipes.json"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def main():
    conn = get_conn()
    cur = conn.cursor()

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    updated = 0
    skipped = 0

    for r in recipes:
        title = (r.get("title") or "").strip()
        if not title:
            continue

        ingredients = r.get("ingredients") or []
        instructions = r.get("instructions") or []
        prep_instructions = "\n".join(instructions)

        # Look for existing recipe by title
        cur.execute(
            "SELECT id, prep_instructions FROM recipes WHERE lower(title) = lower(?)",
            (title.lower(),),
        )
        row = cur.fetchone()

        if not row:
            skipped += 1
            continue

        recipe_id = row["id"]

        # Only overwrite if DB has no prep_instructions yet
        if not (row["prep_instructions"] or "").strip() and prep_instructions:
            cur.execute(
                "UPDATE recipes SET prep_instructions = ? WHERE id = ?",
                (prep_instructions, recipe_id),
            )

        # Sync ingredients into ingredients + recipe_ingredients tables
        for ing in ingredients:
            if not ing or not isinstance(ing, str):
                continue

            cur.execute(
                "INSERT OR IGNORE INTO ingredients (name) VALUES (?)",
                (ing,),
            )
            cur.execute("SELECT id FROM ingredients WHERE name = ?", (ing,))
            ing_row = cur.fetchone()
            if not ing_row:
                continue

            ing_id = ing_row["id"]

            cur.execute(
                """
                INSERT OR IGNORE INTO recipe_ingredients
                (recipe_id, ingredient_id, quantity, unit)
                VALUES (?, ?, ?, ?)
                """,
                (recipe_id, ing_id, None, None),
            )

        updated += 1

    conn.commit()
    conn.close()

    print(f"Updated recipes: {updated}")
    print(f"Skipped recipes: {skipped}")


if __name__ == "__main__":
    main()
