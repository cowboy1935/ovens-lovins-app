(function () {
    const USER_KEY = "ol_user_id";

    function getUserId() {
        let id = localStorage.getItem(USER_KEY);
        if (!id) {
            if (window.crypto && crypto.randomUUID) {
                id = crypto.randomUUID();
            } else {
                id = "user-" + Date.now() + "-" + Math.random().toString(16).slice(2);
            }
            localStorage.setItem(USER_KEY, id);
        }
        return id;
    }

    async function apiFetch(path, options = {}) {
        const userId = getUserId();
        const headers = {
            ...(options.headers || {}),
            "X-User-Id": userId
        };

        const res = await fetch(path, { ...options, headers });
        const text = await res.text();

        if (!res.ok) {
            console.error("API error:", path, res.status, text);
            throw new Error(`Request failed: ${res.status}`);
        }

        try {
            return text ? JSON.parse(text) : null;
        } catch {
            return text;
        }
    }

    const api = {
        getUserId,

        // Recipes
        getRecipes() {
            return apiFetch("/recipes");
        },
        getRecipe(id) {
            return apiFetch(`/recipe/${id}`);
        },
        createRecipe(recipe) {
            return apiFetch("/recipes", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(recipe)
            });
        },
        favoriteRecipe(id) {
            return apiFetch(`/favorite/${id}`, { method: "POST" });
        },
        unfavoriteRecipe(id) {
            return apiFetch(`/unfavorite/${id}`, { method: "POST" });
        },
        getFavorites() {
            return apiFetch("/favorites");
        },
        deleteRecipe(id) {
            return apiFetch(`/recipe/${id}`, { method: "DELETE" });
        },

        // Grocery
        addIngredientsFromRecipe(id) {
            return apiFetch(`/grocery/add_from_recipe/${id}`, { method: "POST" });
        },
        getGroceryList() {
            return apiFetch("/grocery/list");
        },
        addGrocery(item) {
            return apiFetch("/grocery", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(item)
            });
        },
        checkGrocery(id) {
            return apiFetch(`/grocery/check/${id}`, { method: "POST" });
        },
        deleteGrocery(id) {
            return apiFetch(`/grocery/delete/${id}`, { method: "DELETE" });
        },

        // Photos
        getRecipeImages(recipeId) {
            return apiFetch(`/recipe/${recipeId}/images`);
        },
        uploadRecipeImage(recipeId, file, caption = "") {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("caption", caption);

            return apiFetch(`/recipe/${recipeId}/upload_image`, {
                method: "POST",
                body: formData
            });
        },
        deleteRecipeImage(imageId) {
            return apiFetch(`/recipe/images/${imageId}`, {
                method: "DELETE"
            });
        }
    };

    window.api = api;
})();
