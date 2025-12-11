window.api = {
    base: "",

    async getRecipes() {
        const res = await fetch(`${this.base}/recipes`);
        return await res.json();
    },

    async getRecipe(id) {
        const res = await fetch(`${this.base}/recipe/${id}`);  // <-- fixed
        return await res.json();
    },

    async addIngredientsFromRecipe(id) {
        return await fetch(`${this.base}/grocery/add_from_recipe/${id}`, {
            method: "POST"
        });
    },

    async getGroceryList() {
        const res = await fetch(`${this.base}/grocery/list`);
        return await res.json();
    },

    async deleteGrocery(id) {
        return await fetch(`${this.base}/grocery/delete/${id}`, {
            method: "DELETE"
        });
    }
};
