# -----------------------------------------
# Ovens Lovin's – The Kitchen Helper (Backend)
# FINAL PRODUCTION VERSION
# -----------------------------------------

from fastapi import FastAPI, HTTPException, UploadFile, File
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


class GroceryItemIn(BaseModel):
    ingredient_name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None


class GroceryItemOut(GroceryItemIn):
    id: int
    checked: bool = False



# -----------------------------------------
# FAVORITES
# -----------------------------------------

@app.post("/favorite/{recipe_id}")
def favorite(recipe_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE recipes SET is_favorite = 1 WHERE id = ?", (recipe_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.post("/unfavorite/{recipe_id}")
def unfavorite(recipe_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE recipes SET is_favorite = 0 WHERE id = ?", (recipe_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/favorites")
def get_favorites():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, title, meal_type, category, source_type, is_favorite FROM recipes WHERE is_favorite = 1")
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "title": r["title"],
            "meal_type": r["meal_type"],
            "category": r["category"],
            "source_type": r["source_type"],
            "is_favorite": bool(r["is_favorite"])
        }
        for r in rows
    ]


# -----------------------------------------
# RECIPE ENDPOINTS
# -----------------------------------------

@app.get("/recipes")
def list_recipes():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM recipes ORDER BY id ASC")
    rows = cur.fetchall()
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
                is_favorite=bool(r["is_favorite"]),
                linked_budget=None,
                linked_chef=None,
                ingredients=[]
            )
        )
    return recipes


@app.get("/recipe/{recipe_id}")
def get_recipe(recipe_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""SELECT * FROM recipes WHERE id = ?""", (recipe_id,))
    recipe = cur.fetchone()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

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

    conn.close()

    return RecipeOut(
        id=recipe["id"],
        title=recipe["title"],
        meal_type=recipe["meal_type"],
        category=recipe["category"],
        source_type=recipe["source_type"],
        is_budget_friendly=bool(recipe["is_budget_friendly"]),
        base_recipe_id=recipe["base_recipe_id"],
        prep_instructions=recipe["prep_instructions"],
        cook_instructions=recipe["cook_instructions"],
        is_favorite=bool(recipe["is_favorite"]),
        linked_budget=None,
        linked_chef=None,
        ingredients=ingredients
    )


# -----------------------------------------
# GROCERY LIST
# -----------------------------------------

class GroceryItemOut(GroceryItemIn):
    id: int
    checked: bool = False

@app.get("/grocery/list", response_model=List[GroceryItemOut])
def grocery_list():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, ingredient_name, quantity, unit, checked
        FROM grocery_items
        ORDER BY id DESC
    """)
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



@app.post("/grocery", response_model=GroceryItemOut)
def add_grocery(item: GroceryItemIn):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO grocery_items (ingredient_name, quantity, unit)
        VALUES (?, ?, ?)
    """, (item.ingredient_name, item.quantity, item.unit))
    item_id = cur.lastrowid
    conn.commit()
    conn.close()

    return GroceryItemOut(id=item_id, **item.dict())


@app.post("/grocery/check/{item_id}")
def check_item(item_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE grocery_items SET checked = 1 WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.delete("/grocery/delete/{item_id}")
def delete_item(item_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM grocery_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}


# -----------------------------------------
# IMAGE UPLOAD FOR RECIPES
# -----------------------------------------

from datetime import datetime

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
