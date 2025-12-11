import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "recipes.db"
JSON_PATH = Path(__file__).parent / "recipes.json"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def slugify(title: str) -> str:
    return (
        title.strip()
        .lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace("\"", "")
    )

def find_duplicate(cur, title):
    cur.execute("SELECT id FROM recipes WHERE lower(title) = lower(?)", (title,))
    row = cur.fetchone()
    return row["id"] if row else None

def import_recipes():
    conn = get_conn()
    cur = conn.cursor()

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    count_imported = 0
    count_skipped = 0

    for r in recipes:
        title = r.get("title", "").strip()
        if not title:
            print("Skipping recipe with no title.")
            continue

        # Duplicate check
        exists = find_duplicate(cur, title)
        if exists:
            print(f"Skipping duplicate: {title}")
            count_skipped += 1
            continue  # <-- THIS AVOIDS THE recipe_id ISSUE

        slug = slugify(title)

        # Ensure slug is unique
        cur.execute("SELECT id FROM recipes WHERE slug = ?", (slug,))
        slug_exists = cur.fetchone()

        if slug_exists:
            # Generate unique slug: beef-wellington-2, beef-wellington-3, etc.
            num = 2
            while True:
                new_slug = f"{slug}-{num}"
                cur.execute("SELECT id FROM recipes WHERE slug = ?", (new_slug,))
                if not cur.fetchone():
                    slug = new_slug
                    break
                num += 1

        meal_type = None
        category = r.get("category")
        prep_instructions = "\n".join(r.get("instructions", []))
        cook_instructions = ""

        # Insert recipe
        try:
            cur.execute(
                """
                INSERT INTO recipes
                (title, slug, meal_type, category, source_type, is_budget_friendly,
                 base_recipe_id, prep_instructions, cook_instructions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    slug,
                    meal_type,
                    category,
                    "chef",
                    0,
                    None,
                    prep_instructions,
                    cook_instructions,
                )
            )
            recipe_id = cur.lastrowid
        except sqlite3.Error as e:
            print(f"Error inserting recipe {title}: {e}")
            continue

        # Insert ingredients
        for ing in r.get("ingredients", []):
            # Skip null, None, empty, or non-string ingredients
            if not ing or not isinstance(ing, str):
                print(f"Skipping invalid ingredient in {title}: {ing}")
                continue

            try:
                cur.execute("INSERT OR IGNORE INTO ingredients (name) VALUES (?)", (ing,))
                cur.execute("SELECT id FROM ingredients WHERE name = ?", (ing,))
                ing_row = cur.fetchone()

                if ing_row is None:
                    print(f"Ingredient lookup failed for {title}: {ing}")
                    continue

                ing_id = ing_row["id"]

                cur.execute(
                    """
                    INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit)
                    VALUES (?, ?, ?, ?)
                    """,
                    (recipe_id, ing_id, None, None),
                )
            except sqlite3.Error as e:
                print(f"Error inserting ingredient {ing} for recipe {title}: {e}")
                continue

        count_imported += 1

    conn.commit()
    conn.close()

    print("\n========================")
    print(f"Imported recipes: {count_imported}")
    print(f"Skipped duplicates: {count_skipped}")
    print("========================")

if __name__ == "__main__":
    import_recipes()