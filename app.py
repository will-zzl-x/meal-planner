import streamlit as st
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.core.services.body_composition_service import BodyCompositionService
from src.core.services.calorie_banking_service import CalorieBankingService
from src.core.services.macro_tracking_service import MacroTrackingService
from src.core.services.enhanced_grocery_generator import EnhancedGroceryListGenerator
from src.core.services.smart_inventory_service import SmartInventoryService
from src.repositories.sqlite.user_repository import SQLiteUserRepository
from src.repositories.sqlite.recipe_repository import SQLiteRecipeRepository
from src.repositories.sqlite.calorie_tracking_repository import SQLiteCalorieTrackingRepository
from src.repositories.database_manager import DatabaseManager

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
    db_manager = DatabaseManager()
    user_repo = SQLiteUserRepository(db_manager)
    recipe_repo = SQLiteRecipeRepository(db_manager)
    calorie_repo = SQLiteCalorieTrackingRepository(db_manager)
    
    return {
        'body_comp': BodyCompositionService(),
        'calorie_banking': CalorieBankingService(),
        'macro_tracking': MacroTrackingService(),
        'grocery_generator': EnhancedGroceryListGenerator(recipe_repo),
        'inventory': SmartInventoryService(),
        'user_repo': user_repo,
        'recipe_repo': recipe_repo,
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
    st.header("Meal Planning")
    st.info("Meal planning interface with drag-and-drop coming in Task 5.2")

def grocery_lists_page():
    st.header("Grocery Lists")
    st.info("Enhanced grocery list features coming soon")

def inventory_page():
    st.header("Smart Inventory")
    st.info("Inventory management interface coming soon")

def profile_page():
    st.header("Profile Settings")
    st.info("User profile and settings coming soon")

def premium_features_page():
    st.header("Premium Features")
    st.success("Welcome to Premium! 🌟")
    st.info("Advanced premium features coming in Task 5.3")

if __name__ == "__main__":
    main()
