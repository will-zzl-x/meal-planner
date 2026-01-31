# Meal Planner - Collaboration Guide

## Project Status
- **Current Phase**: 80% Complete (4/5 phases done)
- **Next Phase**: Streamlit UI Implementation
- **Architecture**: Clean Architecture with comprehensive backend

## Quick Start for Collaborators

### Setup
```bash
git clone <repository-url>
cd meal-planner
pip install -r requirements.txt
```

### Run Tests
```bash
python -m pytest src/core/services/test_*.py -v
python -m pytest src/repositories/test_*.py -v
```

### Demo Current Features
```bash
python src/web/cli_demo.py
```

## Branch Strategy

### Main Branches
- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - Individual feature development

### Current Development
- **Phase 5**: `feature/streamlit-ui`
  - Task 5.1: Core UI components
  - Task 5.2: Meal planning interface  
  - Task 5.3: Premium features integration

## Key Architecture

### Services (Complete)
- `BodyCompositionService` - Photo-based BF% assessment
- `CalorieBankingService` - Weekly calorie distribution
- `MacroTrackingService` - Protein/carbs/fats targeting
- `EnhancedGroceryListGenerator` - Recipe-based shopping
- `SmartInventoryService` - Expiration tracking

### Repository Layer (Complete)
- User isolation and security validation
- SQLite with proper relationships
- Migration system ready

### UI Layer (Next Phase)
- Streamlit-based web interface
- Drag-and-drop meal planning
- Premium subscription integration

## Development Guidelines

### Code Standards
- Clean Architecture principles
- Comprehensive test coverage
- Type hints and documentation
- Security validation in domain models

### Commit Messages
```
feat: add new feature
fix: bug fix
docs: documentation update
test: add/update tests
refactor: code refactoring
```

### Testing Requirements
- All services must have unit tests
- Repository tests with in-memory database
- Integration tests for critical paths

## Business Model
- **FREE**: Basic meal planning + upgrade prompts
- **PREMIUM**: Smart suggestions + advanced features
- Ready for subscription integration

## Contact & Questions
See `PROJECT_PROGRESS.md` for detailed implementation status.
