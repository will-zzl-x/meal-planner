import streamlit as st
from ..models.recipe import Recipe
from ..models.storage import RecipeStorage
from ..services.shopping_list import ShoppingListAggregator


def main():
    st.title("Meal Planner")
    
    storage = RecipeStorage("data/recipes.csv")
    
    tab1, tab2, tab3 = st.tabs(["Recipes", "Meal Planning", "Shopping List"])
    
    with tab1:
        st.header("Recipe Management")
        
        # Add new recipe
        with st.form("add_recipe"):
            name = st.text_input("Recipe Name")
            ingredients_text = st.text_area("Ingredients (one per line, format: ingredient:quantity)")
            servings = st.number_input("Servings", min_value=1, value=4)
            
            if st.form_submit_button("Add Recipe"):
                if name and ingredients_text:
                    ingredients = [line.strip() for line in ingredients_text.split('\n') if line.strip()]
                    recipe = Recipe(name, ingredients, servings)
                    storage.save_recipe(recipe)
                    st.success(f"Recipe '{name}' added!")
        
        # Display existing recipes
        recipes = storage.load_recipes()
        if recipes:
            st.subheader("Existing Recipes")
            for recipe in recipes:
                with st.expander(f"{recipe.name} (serves {recipe.servings})"):
                    for ingredient in recipe.ingredients:
                        st.write(f"• {ingredient}")
                    if st.button(f"Delete {recipe.name}", key=f"delete_{recipe.name}"):
                        storage.delete_recipe(recipe.name)
                        st.rerun()
    
    with tab2:
        st.header("Meal Planning")
        st.write("Meal planning feature coming soon!")
    
    with tab3:
        st.header("Shopping List")
        st.write("Shopping list feature coming soon!")


if __name__ == "__main__":
    main()
