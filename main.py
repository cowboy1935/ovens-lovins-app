# -----------------------------------------
# Ovens Lovin's – The Kitchen Helper (Backend)
# FINAL PRODUCTION VERSION
# -----------------------------------------

from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
import sqlite3
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os


# -----------------------------------------
# ENVIRONMENT VARIABLES / CLOUDINARY CONFIG
# -----------------------------------------

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


# -----------------------------------------
# DATABASE CONFIG
# -----------------------------------------

DB_PATH = Path(__file__).parent / "recipes.db"
print("USING DATABASE:", DB_PATH)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Per-user favorites join table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_favorites (
            user_id TEXT NOT NULL,
            recipe_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, recipe_id)
        )
    """)

    # user_id column on grocery_items
    cur.execute("PRAGMA table_info(grocery_items)")
    cols = [row["name"] for row in cur.fetchall()]
    if "user_id" not in cols:
        cur.execute("ALTER TABLE grocery_items ADD COLUMN user_id TEXT")
        conn.commit()

    conn.close()

def auto_category(title: str) -> str:
    t = (title or "").lower()

    if any(word in t for word in ["salad"]):
        return "Salad"
    if any(word in t for word in ["soup", "stew", "chowder", "broth"]):
        return "Soups & Stews"
    if any(word in t for word in ["pasta", "spaghetti", "noodle", "lasagna"]):
        return "Pasta"
    if "chicken" in t:
        return "Chicken"
    if any(word in t for word in ["beef", "steak", "burger"]):
        return "Beef"
    if any(word in t for word in ["pork", "ham", "bacon"]):
        return "Pork"
    if any(word in t for word in ["fish", "salmon", "shrimp", "prawn", "crab"]):
        return "Seafood"
    if any(word in t for word in ["cake", "cookie", "brownie", "pie", "tart", "crumble", "dessert"]):
        return "Dessert"
    if any(word in t for word in ["sandwich", "wrap", "taco", "quesadilla"]):
        return "Handhelds"

    return "Other"
   
def normalize_user_id(x_user_id: Optional[str]) -> str:
    return x_user_id or "anon"

# Call on startup
init_db()

# -----------------------------------------
# FASTAPI APP
# -----------------------------------------

app = FastAPI(title="Ovens Lovin's – The Kitchen Helper")


# -----------------------------------------
# STATIC FILE MOUNTS  (match your filesystem)
# -----------------------------------------

app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js", StaticFiles(directory="js"), name="js")
app.mount("/icons", StaticFiles(directory="icons"), name="icons")


# -----------------------------------------
# CORS (Allows PWA install + local requests)
# -----------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# -----------------------------------------
# PWA FILES (Manifest & Service Worker)
# -----------------------------------------

@app.get("/manifest.json", include_in_schema=False)
def manifest():
    return FileResponse("manifest.json")


@app.get("/service-worker.js", include_in_schema=False)
def service_worker():
    return FileResponse("service-worker.js")


# -----------------------------------------
# PAGE ROUTES (Serve HTML directly)
# -----------------------------------------

@app.get("/", include_in_schema=False)
def root():
    return FileResponse("index.html")


@app.get("/index.html", include_in_schema=False)
def serve_index():
    return FileResponse("index.html")


@app.get("/upload.html", include_in_schema=False)
def serve_upload():
    return FileResponse("upload.html")


@app.get("/recipe.html", include_in_schema=False)
def serve_recipe():
    return FileResponse("recipe.html")


@app.get("/grocery.html", include_in_schema=False)
def serve_grocery():
    return FileResponse("grocery.html")


# -----------------------------------------
# DATA MODELS
# -----------------------------------------

class IngredientIn(BaseModel):
    name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None


class RecipeIn(BaseModel):
    title: str
    meal_type: str
    category: Optional[str] = None
    source_type: str = "chef"
    is_budget_friendly: bool = False
    base_recipe_id: Optional[int] = None
    prep_instructions: str
    cook_instructions: str
    ingredients: List[IngredientIn]


class RecipeOut(BaseModel):
    id: int
    title: str
    meal_type: Optional[str] = None
    category: Optional[str] = None
    source_type: str
    is_budget_friendly: bool
    base_recipe_id: Optional[int] = None
    prep_instructions: Optional[str]
    cook_instructions: Optional[str]
    is_favorite: bool = False
    linked_budget: Optional[dict] = None
    linked_chef: Optional[dict] = None
    ingredients: List[dict] = Field(default_factory=list)
    source_url: Optional[str] = None  # 👈 add this


class GroceryItemIn(BaseModel):
    ingredient_name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None


class GroceryItemOut(GroceryItemIn):
    id: int
    checked: bool = False

@app.post("/recipes")
def create_recipe(recipe: RecipeIn):
    """
    Create a new recipe (used by the Add Recipe page).
    """
    conn = get_conn()
    cur = conn.cursor()

    # 1) Category: use given or auto-detect from title
    category = recipe.category or auto_category(recipe.title)

    # 2) Simple slug from title, kept unique
    base_slug = recipe.title.strip().lower().replace(" ", "-")
    slug = base_slug or None

    if slug:
        suffix = 2
        while True:
            cur.execute("SELECT id FROM recipes WHERE slug = ?", (slug,))
            if not cur.fetchone():
                break
            slug = f"{base_slug}-{suffix}"
            suffix += 1

    # 3) Insert into recipes
    cur.execute(
        """
        INSERT INTO recipes
        (title, slug, meal_type, category, source_type, is_budget_friendly,
         base_recipe_id, prep_instructions, cook_instructions, source_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            recipe.title,
            slug,
            recipe.meal_type,
            category,
            recipe.source_type,                        # "custom" from upload.html
            1 if recipe.is_budget_friendly else 0,
            recipe.base_recipe_id,
            recipe.prep_instructions,
            recipe.cook_instructions,
            None,                                      # no external URL for user recipes
        ),
    )
    recipe_id = cur.lastrowid

    # 4) Ingredients: ensure names exist, then link in recipe_ingredients
    for ing in recipe.ingredients:
        # skip completely empty rows
        if not ing.name.strip():
            continue

        cur.execute("INSERT OR IGNORE INTO ingredients (name) VALUES (?)", (ing.name,))
        cur.execute("SELECT id FROM ingredients WHERE name = ?", (ing.name,))
        row = cur.fetchone()
        if not row:
            continue

        ingredient_id = row["id"]

        cur.execute(
            """
            INSERT INTO recipe_ingredients
            (recipe_id, ingredient_id, quantity, unit)
            VALUES (?, ?, ?, ?)
            """,
            (recipe_id, ingredient_id, ing.quantity, ing.unit),
        )

    conn.commit()
    conn.close()

    # 5) Frontend only really needs the new ID
    return {"id": recipe_id}

# -----------------------------------------
# FAVORITES
# -----------------------------------------

@app.post("/favorite/{recipe_id}")
def favorite(recipe_id: int, x_user_id: Optional[str] = Header(default=None)):
    user_id = normalize_user_id(x_user_id)
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM recipes WHERE id = ?", (recipe_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Recipe not found")

    cur.execute("""
        INSERT OR IGNORE INTO user_favorites (user_id, recipe_id)
        VALUES (?, ?)
    """, (user_id, recipe_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.post("/unfavorite/{recipe_id}")
def unfavorite(recipe_id: int, x_user_id: Optional[str] = Header(default=None)):
    user_id = normalize_user_id(x_user_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM user_favorites
        WHERE user_id = ? AND recipe_id = ?
    """, (user_id, recipe_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/favorites")
def get_favorites(x_user_id: Optional[str] = Header(default=None)):
    user_id = normalize_user_id(x_user_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.id, r.title, r.meal_type, r.category, r.source_type
        FROM recipes r
        JOIN user_favorites uf ON uf.recipe_id = r.id
        WHERE uf.user_id = ?
        ORDER BY r.title COLLATE NOCASE
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        cat = r["category"] if r["category"] else auto_category(r["title"])
        result.append(
            {
                "id": r["id"],
                "title": r["title"],
                "meal_type": r["meal_type"],
                "category": cat,
                "source_type": r["source_type"],
                "is_favorite": True,
            }
        )
    return result

# -----------------------------------------
# RECIPE ENDPOINTS
# -----------------------------------------

@app.post("/recipes")
def create_recipe(recipe: RecipeIn):
    """
    Create a new recipe (user-added) and attach its ingredients.
    Uses auto_category() if no category is provided.
    """
    conn = get_conn()
    cur = conn.cursor()

    # Decide category automatically if missing
    category = recipe.category or auto_category(recipe.title)

    # Let source_type come from the payload, but default "custom" for user recipes
    source_type = recipe.source_type or "custom"

    cur.execute("""
        INSERT INTO recipes
            (title, meal_type, category, source_type,
             is_budget_friendly, base_recipe_id,
             prep_instructions, cook_instructions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        recipe.title,
        recipe.meal_type,
        category,
        source_type,
        int(recipe.is_budget_friendly),
        recipe.base_recipe_id,
        recipe.prep_instructions,
        recipe.cook_instructions,
    ))
    recipe_id = cur.lastrowid

    # Attach ingredients
    for ing in recipe.ingredients:
        # make sure we have a name
        if not ing.name:
            continue

        # ensure ingredient exists
        cur.execute(
            "INSERT OR IGNORE INTO ingredients (name) VALUES (?)",
            (ing.name,)
        )
        cur.execute(
            "SELECT id FROM ingredients WHERE name = ?",
            (ing.name,)
        )
        row = cur.fetchone()
        if not row:
            continue

        ing_id = row["id"]
        cur.execute(
            """
            INSERT INTO recipe_ingredients
                (recipe_id, ingredient_id, quantity, unit)
            VALUES (?, ?, ?, ?)
            """,
            (recipe_id, ing_id, ing.quantity, ing.unit)
        )

    conn.commit()
    conn.close()

    # For now, just return the new id – front end can redirect to /recipe.html?id={id}
    return {"id": recipe_id}


@app.get("/recipes")
def list_recipes(x_user_id: Optional[str] = Header(default=None)):
    user_id = normalize_user_id(x_user_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM recipes ORDER BY id ASC")
    rows = cur.fetchall()

    cur.execute("SELECT recipe_id FROM user_favorites WHERE user_id = ?", (user_id,))
    fav_ids = {row["recipe_id"] for row in cur.fetchall()}

    conn.close()

    recipes = []
    for r in rows:
        recipes.append(
            RecipeOut(
                id=r["id"],
                title=r["title"],
                meal_type=r["meal_type"],
                category=r["category"],
                source_type=r["source_type"],
                is_budget_friendly=bool(r["is_budget_friendly"]),
                base_recipe_id=r["base_recipe_id"],
                prep_instructions=r["prep_instructions"],
                cook_instructions=r["cook_instructions"],
                is_favorite=(r["id"] in fav_ids),
                linked_budget=None,
                linked_chef=None,
                ingredients=[],
                source_url=r["source_url"] if "source_url" in r.keys() else None,
            )
        )
    return recipes


@app.get("/recipe/{recipe_id}")
def get_recipe(recipe_id: int, x_user_id: Optional[str] = Header(default=None)):
    user_id = normalize_user_id(x_user_id)
    conn = get_conn()
    cur = conn.cursor()

    # Main recipe row
    cur.execute("""SELECT * FROM recipes WHERE id = ?""", (recipe_id,))
    recipe = cur.fetchone()
    if not recipe:
        conn.close()
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Ingredients
    cur.execute("""
        SELECT ingredients.name, recipe_ingredients.quantity, recipe_ingredients.unit
        FROM recipe_ingredients
        JOIN ingredients ON ingredients.id = recipe_ingredients.ingredient_id
        WHERE recipe_id = ?
    """, (recipe_id,))
    ingredients = [
        {"name": row["name"], "quantity": row["quantity"], "unit": row["unit"]}
        for row in cur.fetchall()
    ]

    # Per-user favorite
    cur.execute("""
        SELECT 1 FROM user_favorites
        WHERE user_id = ? AND recipe_id = ?
    """, (user_id, recipe_id))
    is_favorite = cur.fetchone() is not None

    conn.close()

    cat = recipe["category"] if recipe["category"] else auto_category(recipe["title"])

    return RecipeOut(
        id=recipe["id"],
        title=recipe["title"],
        meal_type=recipe["meal_type"],
        category=cat,
        source_type=recipe["source_type"],
        is_budget_friendly=bool(recipe["is_budget_friendly"]),
        base_recipe_id=recipe["base_recipe_id"],
        prep_instructions=recipe["prep_instructions"],
        cook_instructions=recipe["cook_instructions"],
        is_favorite=is_favorite,
        linked_budget=None,
        linked_chef=None,
        ingredients=ingredients,
        source_url=recipe["source_url"] if "source_url" in recipe.keys() else None,
    )

@app.delete("/recipe/{recipe_id}")
def delete_recipe(recipe_id: int):
    conn = get_conn()
    cur = conn.cursor()

    # Delete linked images
    cur.execute("DELETE FROM recipe_images WHERE recipe_id = ?", (recipe_id,))
    # Delete ingredient links
    cur.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
    # Delete the recipe itself
    cur.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))

    conn.commit()
    conn.close()
    return {"status": "deleted"}



# -----------------------------------------
# GROCERY LIST
# -----------------------------------------

@app.get("/grocery/list", response_model=List[GroceryItemOut])
def grocery_list(x_user_id: Optional[str] = Header(default=None)):
    user_id = normalize_user_id(x_user_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, ingredient_name, quantity, unit, checked
        FROM grocery_items
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))
    items = cur.fetchall()
    conn.close()

    return [
        GroceryItemOut(
            id=i["id"],
            ingredient_name=i["ingredient_name"],
            quantity=i["quantity"],
            unit=i["unit"],
            checked=bool(i["checked"])
        )
        for i in items
    ]


@app.post("/grocery/add_from_recipe/{recipe_id}")
def add_grocery_from_recipe(recipe_id: int, x_user_id: Optional[str] = Header(default=None)):
    """
    Take all ingredients from a recipe and add them as grocery_items
    for the current user.
    """
    user_id = normalize_user_id(x_user_id)

    conn = get_conn()
    cur = conn.cursor()

    # Make sure recipe exists
    cur.execute("SELECT id, title FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cur.fetchone()
    if not recipe:
        conn.close()
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Pull ingredients for this recipe
    cur.execute(
        """
        SELECT ingredients.name AS ingredient_name,
               recipe_ingredients.quantity,
               recipe_ingredients.unit
        FROM recipe_ingredients
        JOIN ingredients
          ON ingredients.id = recipe_ingredients.ingredient_id
        WHERE recipe_ingredients.recipe_id = ?
        """,
        (recipe_id,)
    )
    rows = cur.fetchall()

    added = 0
    for row in rows:
        cur.execute(
            """
            INSERT INTO grocery_items (ingredient_name, quantity, unit, user_id)
            VALUES (?, ?, ?, ?)
            """,
            (row["ingredient_name"], row["quantity"], row["unit"], user_id)
        )
        added += 1

    conn.commit()
    conn.close()

    return {"status": "ok", "recipe_id": recipe_id, "items_added": added}


@app.post("/grocery", response_model=GroceryItemOut)
def add_grocery(item: GroceryItemIn, x_user_id: Optional[str] = Header(default=None)):
    user_id = normalize_user_id(x_user_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO grocery_items (ingredient_name, quantity, unit, user_id)
        VALUES (?, ?, ?, ?)
    """, (item.ingredient_name, item.quantity, item.unit, user_id))
    item_id = cur.lastrowid
    conn.commit()
    conn.close()

    return GroceryItemOut(id=item_id, **item.dict(), checked=False)


@app.post("/grocery/check/{item_id}")
def check_item(item_id: int, x_user_id: Optional[str] = Header(default=None)):
    user_id = normalize_user_id(x_user_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE grocery_items
        SET checked = 1
        WHERE id = ? AND user_id = ?
    """, (item_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.delete("/grocery/delete/{item_id}")
def delete_item(item_id: int, x_user_id: Optional[str] = Header(default=None)):
    user_id = normalize_user_id(x_user_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM grocery_items
        WHERE id = ? AND user_id = ?
    """, (item_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "deleted"}


# -----------------------------------------
# IMAGE UPLOAD FOR RECIPES
# -----------------------------------------

# List images for a recipe
@app.get("/recipe/{recipe_id}/images")
def list_recipe_images(recipe_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, url, caption, created_at FROM recipe_images WHERE recipe_id = ? ORDER BY created_at DESC",
        (recipe_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "url": r["url"],
            "caption": r["caption"],
            "created_at": r["created_at"]
        }
        for r in rows
    ]


# Upload + register a new image with caption
@app.post("/recipe/{recipe_id}/upload_image")
async def upload_recipe_image(recipe_id: int, file: UploadFile = File(...), caption: str = ""):
    try:
        result = cloudinary.uploader.upload(file.file, overwrite=False)
        url = result["secure_url"]

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO recipe_images (recipe_id, url, caption, created_at) VALUES (?, ?, ?, ?)",
            (recipe_id, url, caption, datetime.utcnow())
        )
        conn.commit()
        conn.close()

        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Delete image
@app.delete("/recipe/images/{image_id}")
def delete_recipe_image(image_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM recipe_images WHERE id = ?", (image_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}


# -----------------------------------------
# END OF FILE
# -----------------------------------------

