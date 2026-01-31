# Implementation Plan - Meal Planning App with Flexible Dieting
# Discrete Tasks for Iterative Development

## Phase 1: Technical Debt Remediation & Foundation (Week 1)

### Task 1.1: Service Layer Extraction
**Objective**: Break apart monolithic `GroceryListGenerator`
**Deliverables**:
- `IngredientAggregator` service
- `RecipeScaler` service  
- `UnitConverter` service
- Updated tests
**Test**: Run existing CLI, verify same output

### Task 1.2: Repository Interface Design
**Objective**: Create abstraction layer for data access
**Deliverables**:
- `IRecipeRepository` interface
- `IUserRepository` interface
- `IInventoryRepository` interface
- `ICalorieTrackingRepository` interface (new)
**Test**: Interfaces compile, no implementation yet

### Task 1.3: Database Schema & Migration
**Objective**: SQLite database with multi-user support
**Deliverables**:
- Database schema SQL files
- Migration scripts
- Database initialization utility
**Test**: Database creates successfully, tables exist

## Phase 2: Core Data Layer (Week 2)

### Task 2.1: User Management Repository
**Objective**: Multi-user data isolation
**Deliverables**:
- `SQLiteUserRepository` implementation
- User profile management (weight, body fat %)
- Basic user CRUD operations
**Test**: Can create/retrieve users from database

### Task 2.2: Recipe Repository Implementation
**Objective**: Recipe persistence with user ownership
**Deliverables**:
- `SQLiteRecipeRepository` implementation
- Recipe CRUD with user isolation
- Ingredient relationship management
**Test**: Can save/load recipes per user

### Task 2.3: Calorie Tracking Repository
**Objective**: Daily calorie and macro tracking
**Deliverables**:
- `SQLiteCalorieTrackingRepository` implementation
- Daily log CRUD operations
- Calorie banking calculations
**Test**: Can log daily calories and retrieve history

## Phase 3: Business Logic Services (Week 3)

### Task 3.1: Body Composition Service
**Objective**: Body fat assessment and weight loss calculations
**Deliverables**:
- Body fat percentage photo reference system
- Weight loss percentage calculations
- Daily calorie target generation
**Test**: Can calculate targets from body composition

### Task 3.2: Calorie Banking Service
**Objective**: Weekly calorie distribution and banking logic
**Deliverables**:
- Weekly calorie distribution algorithms
- Banking/borrowing calculations
- Safety threshold enforcement (10 cal/lb minimum)
**Test**: Can redistribute calories while maintaining minimums

### Task 3.3: Macro Tracking Service
**Objective**: Protein, carb, fat tracking alongside calories
**Deliverables**:
- Macro calculation from recipes
- Daily/weekly macro targets
- Macro progress tracking
**Test**: Can track macros from logged meals

## Phase 4: Enhanced Grocery List Integration (Week 4)

### Task 4.1: Meal Planning Service
**Objective**: Connect recipes to daily calorie targets
**Deliverables**:
- Meal assignment to specific days
- Calorie-aware meal suggestions
- Integration with existing grocery list generation
**Test**: Can plan meals that fit daily calorie targets

### Task 4.2: Updated Grocery List Service
**Objective**: Integrate meal planning with shopping lists
**Deliverables**:
- Enhanced `GroceryListService` with meal plan integration
- Inventory management with planned meals
- Multi-day shopping list generation
**Test**: Grocery lists reflect planned meals accurately

## Phase 5: Streamlit UI Implementation (Week 5-6)

### Task 5.1: Basic UI Framework
**Objective**: Multi-page Streamlit app with user sessions
**Deliverables**:
- User authentication/session management
- Navigation between pages
- Dependency injection container for services
**Test**: Can navigate app, maintain user session

### Task 5.2: User Profile & Body Composition UI
**Objective**: User onboarding and profile management
**Deliverables**:
- Body fat percentage photo slider
- Weight/goal input forms
- Calorie target calculation display
**Test**: Can set up user profile, see calculated targets

### Task 5.3: Weekly Planning Interface
**Objective**: Weekly calorie planning and meal assignment
**Deliverables**:
- Weekly calendar view with calorie targets
- Meal planning interface
- Restaurant/special event planning
**Test**: Can plan weekly meals and see calorie distribution

### Task 5.4: Daily Tracking Interface
**Objective**: Daily calorie and macro logging
**Deliverables**:
- Daily food logging interface
- Calorie/macro progress displays
- Banking/borrowing status
**Test**: Can log daily intake, see impact on weekly plan

### Task 5.5: Recipe Management UI
**Objective**: Recipe CRUD with calorie/macro information
**Deliverables**:
- Recipe creation/editing forms
- Recipe library with search/filter
- Macro calculation display
**Test**: Can manage recipes with full nutritional info

### Task 5.6: Enhanced Grocery List UI
**Objective**: Shopping list generation from meal plans
**Deliverables**:
- Grocery list generation from weekly meal plan
- Inventory management interface
- Shopping list export/sharing
**Test**: Can generate accurate shopping lists from meal plans

## Phase 6: Polish & Production Readiness (Week 7)

### Task 6.1: Error Handling & Validation
**Objective**: Robust error handling throughout app
**Deliverables**:
- User-friendly error messages
- Input validation on all forms
- Graceful failure handling
**Test**: App handles invalid inputs gracefully

### Task 6.2: Performance Optimization
**Objective**: Ensure app meets performance requirements
**Deliverables**:
- Database query optimization
- Caching for frequently accessed data
- Response time monitoring
**Test**: All operations complete within specified time limits

### Task 6.3: Documentation & Deployment
**Objective**: Production deployment preparation
**Deliverables**:
- User documentation
- Deployment configuration
- Monitoring setup
**Test**: App deployable and monitorable in production

## Testing Strategy Per Task

**After Each Task**:
1. Run Streamlit app: `streamlit run src/main.py`
2. Verify new functionality works
3. Ensure existing functionality not broken
4. Update tests and documentation

## Success Criteria

**Each task must meet**:
- All EARS requirements satisfied
- No regression in existing functionality
- Code passes security validation
- Performance requirements met
- UI is intuitive for non-technical users

## Risk Mitigation

**High-Risk Tasks**:
- Task 3.2 (Calorie Banking) - Complex algorithm
- Task 5.3 (Weekly Planning UI) - Complex user interaction
- Task 5.6 (Grocery List Integration) - Multiple system integration

**Mitigation**: Extra testing, user feedback sessions, fallback implementations
