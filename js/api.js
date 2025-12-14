// js/api.js

window.api = {
    // ---- Recipes ----
    async getRecipes() {
        const res = await fetch("/recipes");
        if (!res.ok) throw new Error("Failed to load recipes");
        return await res.json();
    },

    async getRecipe(id) {
        const res = await fetch(`/recipe/${id}`);
        if (!res.ok) throw new Error("Failed to load recipe");
        return await res.json();
    },

    async favoriteRecipe(id) {
        const res = await fetch(`/favorite/${id}`, { method: "POST" });
        if (!res.ok) throw new Error("Failed to favorite");
        return await res.json();
    },

    async unfavoriteRecipe(id) {
        const res = await fetch(`/unfavorite/${id}`, { method: "POST" });
        if (!res.ok) throw new Error("Failed to unfavorite");
        return await res.json();
    },

    async getFavorites() {
        const res = await fetch("/favorites");
        if (!res.ok) throw new Error("Failed to load favorites");
        return await res.json();
    },

    async deleteRecipe(id) {
        const res = await fetch(`/recipe/${id}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Failed to delete recipe");
        return await res.json();
    },

    // ---- Grocery ----
    async addIngredientsFromRecipe(id) {
        const res = await fetch(`/grocery/add_from_recipe/${id}`, {
            method: "POST"
        });
        if (!res.ok) throw new Error("Failed to add from recipe");
        return await res.json();
    },

    async getGroceryList() {
        const res = await fetch("/grocery/list");
        if (!res.ok) throw new Error("Failed to load grocery list");
        return await res.json();
    },

    async addGrocery(item) {
        const res = await fetch("/grocery", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(item)
        });
        if (!res.ok) throw new Error("Failed to add grocery item");
        return await res.json();
    },

    async checkGrocery(id) {
        const res = await fetch(`/grocery/check/${id}`, { method: "POST" });
        if (!res.ok) throw new Error("Failed to check grocery item");
        return await res.json();
    },

    async deleteGrocery(id) {
        const res = await fetch(`/grocery/delete/${id}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Failed to delete grocery item");
        return await res.json();
    },

    // ---- Photos ----
    async getRecipeImages(recipeId) {
        const res = await fetch(`/recipe/${recipeId}/images`);
        if (!res.ok) throw new Error("Failed to load images");
        return await res.json();
    },

    async uploadRecipeImage(recipeId, file, caption = "") {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("caption", caption);

        const res = await fetch(`/recipe/${recipeId}/upload_image`, {
            method: "POST",
            body: formData
        });
        if (!res.ok) throw new Error("Failed to upload image");
        return await res.json();
    },

    async deleteRecipeImage(imageId) {
        const res = await fetch(`/recipe/images/${imageId}`, {
            method: "DELETE"
        });
        if (!res.ok) throw new Error("Failed to delete image");
        return await res.json();
    }
};
