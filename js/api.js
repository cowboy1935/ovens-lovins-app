// js/api.js

window.api = {
    base: "",

    async _request(path, options = {}) {
        const res = await fetch(`${this.base}${path}`, {
            headers: {
                "Accept": "application/json",
                ...(options.headers || {})
            },
            ...options
        });

        // If there's no body (204 etc.)
        if (res.status === 204) return null;

        let data;
        try {
            data = await res.json();
        } catch {
            if (!res.ok) {
                throw new Error(`Request failed: ${res.status}`);
            }
            return null;
        }

        if (!res.ok) {
            const msg = data?.detail || data?.error || `Request failed: ${res.status}`;
            throw new Error(msg);
        }

        return data;
    },

    // -------- Recipes --------

    async getRecipes() {
        return this._request("/recipes");
    },

    async getRecipe(id) {
        return this._request(`/recipe/${id}`);
    },

    // Take all ingredients from a recipe into grocery list
    async addIngredientsFromRecipe(id) {
        return this._request(`/grocery/add_from_recipe/${id}`, {
            method: "POST"
        });
    },

    // -------- Grocery --------

    async getGroceryList() {
        return this._request("/grocery/list");
    },

    async deleteGrocery(id) {
        return this._request(`/grocery/delete/${id}`, {
            method: "DELETE"
        });
    },

    // Optional helpers if you want them:

    async addGroceryItem(ingredient_name, quantity = null, unit = null) {
        return this._request("/grocery", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ingredient_name, quantity, unit })
        });
    },

    async checkGroceryItem(id) {
        return this._request(`/grocery/check/${id}`, {
            method: "POST"
        });
    }
};
