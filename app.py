import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.core.services.body_composition_service import BodyCompositionService
from src.core.services.calorie_banking_service import CalorieBankingService
from src.core.services.macro_tracking_service import MacroTrackingService
from src.core.services.smart_inventory_service import SmartInventoryService
from src.repositories.sqlite.user_repository import SQLiteUserRepository
from src.repositories.sqlite.calorie_tracking_repository import SQLiteCalorieTrackingRepository

# Page config
st.set_page_config(
    page_title="Meal Planner Pro",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'is_premium' not in st.session_state:
    st.session_state.is_premium = False

# Initialize services
@st.cache_resource
def init_services():
    db_path = "meal_planner.db"
    user_repo = SQLiteUserRepository(db_path)
    calorie_repo = SQLiteCalorieTrackingRepository(db_path)
    
    return {
        'body_comp': BodyCompositionService(),
        'calorie_banking': CalorieBankingService(),
        'macro_tracking': MacroTrackingService(),
        'inventory': SmartInventoryService(),
        'user_repo': user_repo,
        'calorie_repo': calorie_repo
    }

services = init_services()

def main():
    st.title("🍽️ Meal Planner Pro")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        
        if st.session_state.user_id is None:
            page = st.selectbox("Choose page:", ["Login", "Register"])
        else:
            pages = ["Dashboard", "Meal Planning", "Grocery Lists", "Inventory", "Profile"]
            if st.session_state.is_premium:
                pages.append("Premium Features")
            page = st.selectbox("Choose page:", pages)
            
            if st.button("Logout"):
                st.session_state.user_id = None
                st.session_state.is_premium = False
                st.rerun()
    
    # Route to pages
    if st.session_state.user_id is None:
        if page == "Login":
            login_page()
        else:
            register_page()
    else:
        if page == "Dashboard":
            dashboard_page()
        elif page == "Meal Planning":
            meal_planning_page()
        elif page == "Grocery Lists":
            grocery_lists_page()
        elif page == "Inventory":
            inventory_page()
        elif page == "Profile":
            profile_page()
        elif page == "Premium Features":
            premium_features_page()

def login_page():
    st.header("Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted and username and password:
            # Simple demo login - in production, use proper authentication
            user = services['user_repo'].get_user_by_username(username)
            if user:
                st.session_state.user_id = user.user_id
                st.session_state.is_premium = user.subscription_tier == "premium"
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials")

def register_page():
    st.header("Register")
    
    with st.form("register_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Register")
        
        if submitted and username and email and password:
            try:
                user_id = services['user_repo'].create_user(username, email, password)
                st.session_state.user_id = user_id
                st.session_state.is_premium = False
                st.success("Account created successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Registration failed: {str(e)}")

def dashboard_page():
    st.header("Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Today's Calories", "1,850", "150")
    
    with col2:
        st.metric("Weekly Average", "2,100", "-50")
    
    with col3:
        st.metric("Protein Goal", "85%", "15%")
    
    st.subheader("Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Log Meal", use_container_width=True):
            st.info("Navigate to Meal Planning to log meals")
    
    with col2:
        if st.button("View Grocery List", use_container_width=True):
            st.info("Navigate to Grocery Lists")
    
    with col3:
        if st.button("Check Inventory", use_container_width=True):
            st.info("Navigate to Inventory")
    
    # Premium upgrade prompt for free users
    if not st.session_state.is_premium:
        st.info("🌟 Upgrade to Premium for smart meal suggestions and advanced inventory management!")

def meal_planning_page():
    st.header("🗓️ Weekly Meal Planning")
    
    # Week selector and meal count
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        selected_date = st.date_input("Select week starting:", value=datetime.now().date())
    with col2:
        num_meals = st.number_input("Meals per day:", min_value=1, max_value=8, value=4)
    with col3:
        if st.button("This Week"):
            st.rerun()
    
    # Days of the week
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # Recipe selection sidebar
    with st.sidebar:
        st.subheader("📋 Available Recipes")
        
        # Search recipes
        search_term = st.text_input("Search recipes...")
        
        # Sample recipes (in production, fetch from database)
        sample_recipes = [
            {"name": "Grilled Chicken Breast", "calories": 165, "protein": 31},
            {"name": "Brown Rice Bowl", "calories": 220, "protein": 5},
            {"name": "Greek Yogurt Parfait", "calories": 150, "protein": 15},
            {"name": "Salmon Fillet", "calories": 206, "protein": 22},
            {"name": "Quinoa Salad", "calories": 180, "protein": 8},
            {"name": "Protein Smoothie", "calories": 250, "protein": 25}
        ]
        
        for recipe in sample_recipes:
            if not search_term or search_term.lower() in recipe["name"].lower():
                with st.container():
                    st.write(f"**{recipe['name']}**")
                    st.write(f"🔥 {recipe['calories']} cal | 💪 {recipe['protein']}g protein")
                    if st.button(f"Add to meal plan", key=f"add_{recipe['name']}"):
                        if 'selected_recipes' not in st.session_state:
                            st.session_state.selected_recipes = {}
                        st.session_state.selected_recipes[recipe['name']] = recipe
                        st.success(f"Added {recipe['name']}!")
                    st.divider()
    
    # Weekly meal grid
    st.subheader("Weekly Meal Plan")
    
    # Initialize meal plan in session state with dynamic meal count
    if 'meal_plan' not in st.session_state or 'num_meals' not in st.session_state or st.session_state.num_meals != num_meals:
        st.session_state.num_meals = num_meals
        st.session_state.meal_plan = {day: {f"meal_{i+1}": [] for i in range(num_meals)} for day in days}
    
    # Meal planning grid
    for day in days:
        st.subheader(f"📅 {day}")
        
        cols = st.columns(num_meals)
        for i in range(num_meals):
            with cols[i]:
                meal_key = f"meal_{i+1}"
                st.write(f"**Meal {i+1}**")
                
                # Meal slot container
                meals = st.session_state.meal_plan[day][meal_key]
                
                if meals:
                    for j, meal in enumerate(meals):
                        with st.container():
                            st.write(f"🍽️ {meal}")
                            if st.button("❌", key=f"remove_{day}_{meal_key}_{j}"):
                                st.session_state.meal_plan[day][meal_key].remove(meal)
                                st.rerun()
                else:
                    st.write("*No meals planned*")
                
                # Add meal dropdown
                if 'selected_recipes' in st.session_state and st.session_state.selected_recipes:
                    recipe_options = ["Select recipe..."] + list(st.session_state.selected_recipes.keys())
                    selected_recipe = st.selectbox(
                        "Add meal:", 
                        recipe_options,
                        key=f"select_{day}_{meal_key}"
                    )
                    
                    if selected_recipe != "Select recipe...":
                        if st.button("Add", key=f"add_{day}_{meal_key}"):
                            st.session_state.meal_plan[day][meal_key].append(selected_recipe)
                            st.rerun()
        
        st.divider()
    
    # Daily summaries
    st.subheader("📊 Daily Nutrition Summary")
    
    summary_cols = st.columns(len(days))
    for i, day in enumerate(days):
        with summary_cols[i]:
            total_calories = 0
            total_protein = 0
            
            for meal_num in range(num_meals):
                meal_key = f"meal_{meal_num+1}"
                meals = st.session_state.meal_plan[day][meal_key]
                for meal in meals:
                    if 'selected_recipes' in st.session_state and meal in st.session_state.selected_recipes:
                        recipe = st.session_state.selected_recipes[meal]
                        total_calories += recipe['calories']
                        total_protein += recipe['protein']
            
            st.metric(f"{day[:3]}", f"{total_calories} cal", f"{total_protein}g protein")
    
    # Action buttons
    st.subheader("🎯 Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Generate Grocery List", use_container_width=True):
            st.success("Grocery list generated! Check the Grocery Lists page.")
    
    with col2:
        if st.button("💾 Save Meal Plan", use_container_width=True):
            st.success("Meal plan saved successfully!")
    
    with col3:
        if st.button("🔄 Clear All", use_container_width=True):
            st.session_state.meal_plan = {day: {f"meal_{i+1}": [] for i in range(num_meals)} for day in days}
            st.rerun()
    
    # Premium features teaser
    if not st.session_state.is_premium:
        st.info("🌟 **Premium Feature**: Get smart meal suggestions based on your calorie and macro targets!")
        if st.button("Upgrade to Premium"):
            st.balloons()
            st.success("Upgrade feature coming in Task 5.3!")

def grocery_lists_page():
    st.header("🛒 Smart Grocery Lists")
    
    # Generate from meal plan
    if st.button("📋 Generate from Meal Plan"):
        if 'meal_plan' in st.session_state and 'selected_recipes' in st.session_state:
            # Collect all recipes from meal plan
            all_recipes = []
            for day in st.session_state.meal_plan:
                for meal_type in st.session_state.meal_plan[day]:
                    all_recipes.extend(st.session_state.meal_plan[day][meal_type])
            
            if all_recipes:
                st.success(f"Generated grocery list for {len(set(all_recipes))} unique recipes!")
                
                # Sample grocery list (in production, use EnhancedGroceryListGenerator)
                st.subheader("📝 Your Grocery List")
                
                grocery_items = {
                    "Proteins": ["Chicken breast (2 lbs)", "Salmon fillet (1 lb)", "Greek yogurt (32 oz)"],
                    "Grains": ["Brown rice (2 lbs)", "Quinoa (1 lb)"],
                    "Produce": ["Mixed berries (2 cups)", "Spinach (1 bag)", "Avocado (3 pieces)"],
                    "Pantry": ["Protein powder (1 container)", "Olive oil", "Spices"]
                }
                
                for category, items in grocery_items.items():
                    st.write(f"**{category}:**")
                    for item in items:
                        st.write(f"  • {item}")
                
                if not st.session_state.is_premium:
                    st.info("🌟 **Premium**: Get cost optimization and bulk buying suggestions!")
            else:
                st.warning("No recipes in your meal plan yet. Add some recipes first!")
        else:
            st.warning("Create a meal plan first to generate grocery lists!")
    
    # Manual grocery list
    st.subheader("✏️ Manual Grocery List")
    
    if 'manual_grocery_list' not in st.session_state:
        st.session_state.manual_grocery_list = []
    
    new_item = st.text_input("Add item to grocery list:")
    if st.button("Add Item") and new_item:
        st.session_state.manual_grocery_list.append(new_item)
        st.rerun()
    
    if st.session_state.manual_grocery_list:
        st.write("**Your Manual List:**")
        for i, item in enumerate(st.session_state.manual_grocery_list):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"• {item}")
            with col2:
                if st.button("❌", key=f"remove_manual_{i}"):
                    st.session_state.manual_grocery_list.remove(item)
                    st.rerun()

def inventory_page():
    st.header("📦 Smart Inventory Management")
    
    # Add inventory item
    st.subheader("➕ Add Inventory Item")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        item_name = st.text_input("Item name:")
    with col2:
        quantity = st.number_input("Quantity:", min_value=0.1, value=1.0, step=0.1)
    with col3:
        unit = st.selectbox("Unit:", ["lbs", "oz", "cups", "pieces", "packages"])
    
    col1, col2 = st.columns(2)
    with col1:
        purchase_date = st.date_input("Purchase date:", value=datetime.now().date())
    with col2:
        storage_location = st.selectbox("Storage:", ["Fridge", "Freezer", "Pantry"])
    
    if st.button("Add to Inventory") and item_name:
        if 'inventory' not in st.session_state:
            st.session_state.inventory = []
        
        # Calculate expiration (simplified)
        expiration_days = {"Fridge": 7, "Freezer": 90, "Pantry": 365}
        expiration_date = purchase_date + timedelta(days=expiration_days[storage_location])
        
        item = {
            "name": item_name,
            "quantity": quantity,
            "unit": unit,
            "purchase_date": purchase_date,
            "expiration_date": expiration_date,
            "storage": storage_location
        }
        
        st.session_state.inventory.append(item)
        st.success(f"Added {quantity} {unit} of {item_name} to inventory!")
        st.rerun()
    
    # Current inventory
    if 'inventory' in st.session_state and st.session_state.inventory:
        st.subheader("📋 Current Inventory")
        
        # Sort by expiration date
        sorted_inventory = sorted(st.session_state.inventory, key=lambda x: x['expiration_date'])
        
        for i, item in enumerate(sorted_inventory):
            days_until_expiration = (item['expiration_date'] - datetime.now().date()).days
            
            # Color code by expiration
            if days_until_expiration <= 3:
                status = "🔴 Expires soon!"
                alert_type = "error"
            elif days_until_expiration <= 7:
                status = "🟡 Use this week"
                alert_type = "warning"
            else:
                status = f"🟢 Good for {days_until_expiration} days"
                alert_type = "success"
            
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.write(f"**{item['name']}**")
                    st.write(f"{item['quantity']} {item['unit']} • {item['storage']}")
                
                with col2:
                    st.write(f"Purchased: {item['purchase_date']}")
                    st.write(f"Expires: {item['expiration_date']}")
                
                with col3:
                    if alert_type == "error":
                        st.error(status)
                    elif alert_type == "warning":
                        st.warning(status)
                    else:
                        st.success(status)
                
                with col4:
                    if st.button("🗑️", key=f"delete_inventory_{i}"):
                        st.session_state.inventory.remove(item)
                        st.rerun()
                
                st.divider()
        
        # Premium features teaser
        if not st.session_state.is_premium:
            st.info("🌟 **Premium Features**: Automatic recipe suggestions for expiring items, bulk buying optimization, and waste tracking!")
    else:
        st.info("No items in inventory yet. Add some items to get started!")

def profile_page():
    st.header("Profile Settings")
    st.info("User profile and settings coming soon")

def premium_features_page():
    st.header("Premium Features")
    st.success("Welcome to Premium! 🌟")
    st.info("Advanced premium features coming in Task 5.3")

if __name__ == "__main__":
    main()
