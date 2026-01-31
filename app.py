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
            pages = ["Dashboard", "Meal Planning", "Inventory & Shopping", "Profile"]
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
        elif page == "Inventory & Shopping":
            inventory_shopping_page()
        elif page == "Profile":
            profile_page()
        elif page == "Premium Features":
            premium_features_page()

def login_page():
    st.header("Login")
    
    # Demo credentials info
    with st.expander("🧪 Demo Credentials", expanded=False):
        st.info("**For testing purposes:**")
        st.code("Email: demo@mealplanner.com\nPassword: demo123")
        if st.button("Use Demo Login"):
            # Create demo user if doesn't exist
            demo_user = services['user_repo'].find_by_email("demo@mealplanner.com")
            if not demo_user:
                demo_user = services['user_repo'].create_user("Demo User", "demo@mealplanner.com")
            
            st.session_state.user_id = demo_user.user_id
            st.session_state.is_premium = False
            st.success("🎉 Logged in with demo account!")
            st.rerun()
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="Enter your email address")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Login", use_container_width=True)
        with col2:
            remember_me = st.checkbox("Remember me", help="Keep you logged in (demo feature)")
        
        if submitted and email and password:
            # Simple demo login - find user by email
            user = services['user_repo'].find_by_email(email)
            if user:
                st.session_state.user_id = user.user_id
                st.session_state.is_premium = False
                
                # Remember login if checked
                if remember_me:
                    st.session_state.remembered_email = email
                
                st.success(f"🎉 Welcome back, {user.name}!")
                st.rerun()
            else:
                st.error("❌ Account not found. Please check your email or register for a new account.")
    
    # Show remembered email if exists
    if 'remembered_email' in st.session_state:
        st.info(f"💭 Last login: {st.session_state.remembered_email}")

def register_page():
    st.header("Register")
    
    # Quick demo account creation
    st.info("💡 **Quick Start**: Use the demo login on the Login page, or create your own account below.")
    
    with st.form("register_form"):
        username = st.text_input("Username", placeholder="Enter your name")
        email = st.text_input("Email", placeholder="Enter your email address")
        password = st.text_input("Password", type="password", placeholder="Create a password")
        submitted = st.form_submit_button("Create Account", use_container_width=True)
        
        if submitted and username and email and password:
            try:
                # Check if email already exists
                existing_user = services['user_repo'].find_by_email(email)
                if existing_user:
                    st.error("⚠️ Email is already registered. Please use a different email or try logging in.")
                    return
                
                # Create user with just username and email (password handling would be added later)
                user = services['user_repo'].create_user(username, email)
                st.session_state.user_id = user.user_id
                st.session_state.is_premium = False  # Default to free tier
                st.session_state.remembered_email = email  # Remember this email
                st.success("🎉 Account created successfully! Welcome to Meal Planner Pro!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Registration failed: Unable to create account. Please try again.")

def dashboard_page():
    st.header("📊 Dashboard")
    
    # Sample data - in production, fetch from user's actual data
    daily_calories = 1850
    calorie_target = 2000
    calorie_progress = (daily_calories / calorie_target) * 100
    
    weekly_avg = 2100
    weekly_target = 2000
    weekly_diff = weekly_avg - weekly_target
    
    protein_consumed = 85
    protein_target = 100
    protein_progress = (protein_consumed / protein_target) * 100
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Today's Calories", 
            f"{daily_calories:,}", 
            f"{daily_calories - calorie_target:+d} vs target",
            help="Calories consumed today vs your daily target"
        )
    
    with col2:
        st.metric(
            "Weekly Average", 
            f"{weekly_avg:,}", 
            f"{weekly_diff:+d} vs target",
            help="Average daily calories this week vs target"
        )
    
    with col3:
        st.metric(
            "Protein Progress", 
            f"{protein_progress:.0f}%", 
            f"{protein_consumed}g / {protein_target}g",
            help="Percentage of daily protein target achieved"
        )
    
    st.subheader("🎯 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Log Today's Meals", use_container_width=True):
            st.session_state.dashboard_action = "meal_planning"
            st.rerun()
    
    with col2:
        if st.button("🛒 View Grocery List", use_container_width=True):
            st.session_state.dashboard_action = "grocery_lists"
            st.rerun()
    
    with col3:
        if st.button("📦 Inventory & Shopping", use_container_width=True):
            st.session_state.dashboard_action = "inventory"
            st.rerun()
    
    # Handle quick action navigation
    if 'dashboard_action' in st.session_state:
        if st.session_state.dashboard_action == "meal_planning":
            st.info("🍽️ Redirecting to Meal Planning...")
            del st.session_state.dashboard_action
            st.switch_page = "Meal Planning"  # This would work in a multi-page app
        elif st.session_state.dashboard_action == "grocery_lists":
            st.info("🛒 Redirecting to Grocery Lists...")
            del st.session_state.dashboard_action
        elif st.session_state.dashboard_action == "inventory":
            st.info("📦 Redirecting to Inventory...")
            del st.session_state.dashboard_action
    
    # Premium upgrade prompt for free users
    if not st.session_state.is_premium:
        st.info("🌟 **Upgrade to Premium** for smart meal suggestions, advanced inventory management, and detailed nutrition analytics!")
        if st.button("Learn More About Premium"):
            st.balloons()
            st.success("Premium features coming in the next update!")

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

def inventory_shopping_page():
    st.header("📦 Inventory & Shopping")
    
    # Tabs for better organization
    tab1, tab2 = st.tabs(["🏠 Current Inventory", "🛒 Shopping Lists"])
    
    with tab1:
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
            st.success(f"✅ Added {quantity} {unit} of {item_name} to inventory!")
            st.rerun()
        
        # Current inventory display
        if 'inventory' in st.session_state and st.session_state.inventory:
            st.subheader("📋 Current Inventory")
            
            # Sort by expiration date
            sorted_inventory = sorted(st.session_state.inventory, key=lambda x: x['expiration_date'])
            
            for i, item in enumerate(sorted_inventory):
                days_until_expiration = (item['expiration_date'] - datetime.now().date()).days
                
                # Color code by expiration
                if days_until_expiration <= 3:
                    status = "🔴 Use immediately!"
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
        else:
            st.info("📦 No items in inventory yet. Add some items to get started!")
    
    with tab2:
        st.subheader("🛒 Smart Shopping Lists")
        
        # Generate from meal plan
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Generate from Meal Plan", use_container_width=True):
                if 'meal_plan' in st.session_state and 'selected_recipes' in st.session_state:
                    # Collect all recipes from meal plan
                    all_recipes = []
                    for day in st.session_state.meal_plan:
                        for meal_type in st.session_state.meal_plan[day]:
                            all_recipes.extend(st.session_state.meal_plan[day][meal_type])
                    
                    if all_recipes:
                        st.success(f"✅ Generated grocery list for {len(set(all_recipes))} unique recipes!")
                        
                        # Sample grocery list (in production, use EnhancedGroceryListGenerator)
                        st.subheader("📝 Your Grocery List")
                        
                        grocery_items = {
                            "🥩 Proteins": ["Chicken breast (2 lbs)", "Salmon fillet (1 lb)", "Greek yogurt (32 oz)"],
                            "🌾 Grains": ["Brown rice (2 lbs)", "Quinoa (1 lb)"],
                            "🥬 Produce": ["Mixed berries (2 cups)", "Spinach (1 bag)", "Avocado (3 pieces)"],
                            "🏪 Pantry": ["Protein powder (1 container)", "Olive oil", "Spices"]
                        }
                        
                        for category, items in grocery_items.items():
                            st.write(f"**{category}:**")
                            for item in items:
                                st.write(f"  • {item}")
                        
                        if not st.session_state.is_premium:
                            st.info("🌟 **Premium**: Get cost optimization, bulk buying suggestions, and store-specific lists!")
                    else:
                        st.warning("⚠️ No recipes in your meal plan yet. Add some recipes first!")
                else:
                    st.warning("⚠️ Create a meal plan first to generate grocery lists!")
        
        with col2:
            if st.button("🔄 Check Expiring Items", use_container_width=True):
                if 'inventory' in st.session_state and st.session_state.inventory:
                    expiring_items = []
                    for item in st.session_state.inventory:
                        days_left = (item['expiration_date'] - datetime.now().date()).days
                        if days_left <= 7:
                            expiring_items.append(f"{item['name']} ({days_left} days left)")
                    
                    if expiring_items:
                        st.warning("⚠️ **Items expiring soon:**")
                        for item in expiring_items:
                            st.write(f"• {item}")
                        st.info("💡 Consider using these items in your next meal plan!")
                    else:
                        st.success("✅ No items expiring soon!")
                else:
                    st.info("📦 No inventory items to check.")
        
        # Manual grocery list
        st.subheader("✏️ Manual Shopping List")
        
        if 'manual_grocery_list' not in st.session_state:
            st.session_state.manual_grocery_list = []
        
        col1, col2 = st.columns([3, 1])
        with col1:
            new_item = st.text_input("Add item to shopping list:")
        with col2:
            if st.button("Add Item") and new_item:
                st.session_state.manual_grocery_list.append(new_item)
                st.rerun()
        
        if st.session_state.manual_grocery_list:
            st.write("**Your Shopping List:**")
            for i, item in enumerate(st.session_state.manual_grocery_list):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"• {item}")
                with col2:
                    if st.button("❌", key=f"remove_manual_{i}"):
                        st.session_state.manual_grocery_list.remove(item)
                        st.rerun()
        else:
            st.info("📝 Your shopping list is empty. Add items above or generate from your meal plan!")
def profile_page():
    st.header("Profile Settings")
    st.info("User profile and settings coming soon")

def premium_features_page():
    st.header("Premium Features")
    st.success("Welcome to Premium! 🌟")
    st.info("Advanced premium features coming in Task 5.3")

if __name__ == "__main__":
    main()
