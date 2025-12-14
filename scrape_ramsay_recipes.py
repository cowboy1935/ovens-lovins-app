import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).parent
JSON_PATH = BASE_DIR / "recipes.json"


def parse_recipe_page(html: str):
    """
    Try to extract ingredients list and instructions list
    from a Gordon Ramsay recipe page.
    """
    soup = BeautifulSoup(html, "html.parser")

    ingredients = []
    instructions = []

    # ---- Ingredients ----
    ing_header = soup.find(["h2", "h3"], string=lambda s: s and "ingredients" in s.lower())
    if ing_header:
        for sib in ing_header.find_all_next():
            # Stop when we hit the cooking instructions header
            if sib.name in ["h2", "h3"] and sib.get_text(strip=True).lower().startswith("cooking"):
                break
            # Typical ingredients are in <p> or <li>
            if sib.name in ["p", "li"]:
                text = sib.get_text(" ", strip=True)
                if text:
                    ingredients.append(text)

    # ---- Instructions ----
    inst_header = soup.find(["h2", "h3"], string=lambda s: s and "cooking instructions" in s.lower())
    if inst_header:
        for sib in inst_header.find_all_next():
            if sib.name in ["h2", "h3"]:
                break
            if sib.name in ["p", "li"]:
                text = sib.get_text(" ", strip=True)
                if text:
                    instructions.append(text)

    return ingredients, instructions


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    updated = 0
    skipped = 0

    for r in recipes:
        title = (r.get("title") or "").strip()
        url = r.get("url")

        if not url:
            skipped += 1
            continue

        # Skip ones that already have data
        if r.get("ingredients") or r.get("instructions"):
            skipped += 1
            continue

        print(f"Fetching: {title} -> {url}")
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"  !! Failed to fetch: {e}")
            skipped += 1
            continue

        ingredients, instructions = parse_recipe_page(resp.text)

        if not ingredients and not instructions:
            print("  !! Could not parse ingredients/instructions")
            skipped += 1
            continue

        r["ingredients"] = ingredients
        r["instructions"] = instructions
        updated += 1

        # Be polite to the site – short pause
        time.sleep(1)

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

    print(f"Updated: {updated}, skipped: {skipped}")


if __name__ == "__main__":
    main()
