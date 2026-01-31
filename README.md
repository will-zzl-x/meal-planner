# Meal Planning App - Professional Architecture

A **spec-driven** meal planning application with flexible dieting features, built using enterprise-grade architecture patterns.

## 🏗️ Project Structure

```
meal-planner/
├── .kiro/
│   ├── steering/          # The "Brain" - Core decisions & architecture
│   │   ├── product.md     # Product requirements (EARS format)
│   │   ├── technical.md   # Technical design decisions
│   │   ├── architecture.md # Architecture deep dive & learning
│   │   └── structure.md   # Project governance & best practices
│   └── hooks/             # Automation scripts
│       └── sync-docs.sh   # Auto-sync steering → docs
├── src/
│   ├── core/              # Pure Logic - No dependencies
│   │   ├── models.py      # Data models with security validation
│   │   ├── security.py    # Input validation & sanitization
│   │   └── services/      # Business logic services
│   ├── repositories/      # Data Access - Interface abstractions
│   └── web/               # UI Layer - Streamlit & CLI interfaces
├── specs/                 # The "Contracts" - EARS requirements
├── docs/                  # Generated documentation (auto-synced)
└── tests/                 # Test suite (mirrors src/ structure)
```

## 🎯 Architecture Principles

### Repository + Service Layer Pattern
- **Service Layer**: Pure business logic, no data access
- **Repository Layer**: Data access abstraction, swappable implementations
- **UI Layer**: Presentation only, depends on services

### Multi-User from Day 1
- User isolation at database level
- All operations include user_id for security
- Session management built-in

### Security by Design
- Input validation in data models
- XSS prevention in all user inputs
- SQL injection prevention via parameterized queries

## 🚀 Quick Start

### Run CLI Demo
```bash
cd src/web
python3 cli_demo.py
```

### Run Streamlit UI
```bash
cd src/web  
streamlit run streamlit_app.py
```

### Sync Documentation
```bash
.kiro/hooks/sync-docs.sh
```

## 📋 Current Features

### ✅ Implemented
- **Smart Grocery Lists**: Inventory-aware with practical scaling
- **Recipe Management**: CRUD with security validation
- **Calorie Targeting**: Automatic recipe scaling for calorie goals
- **Multi-User Architecture**: User isolation and session management
- **Professional Structure**: Repository + Service layer pattern

### 🚧 In Development
- **Flexible Dieting**: Weekly calorie banking/borrowing
- **Body Composition**: Photo-based body fat assessment
- **Macro Tracking**: Protein, carbs, fats alongside calories
- **SQLite Integration**: Database persistence layer

## 🎓 Learning Resources

- **Architecture Deep Dive**: `.kiro/steering/architecture.md`
- **Implementation Plan**: `specs/IMPLEMENTATION_PLAN.md`
- **EARS Requirements**: `specs/` folder

## 🔧 Development Workflow

1. **Requirements First**: All features start with EARS requirements
2. **Design Before Code**: Technical design in `.kiro/steering/`
3. **Test-Driven**: Write tests alongside implementation
4. **Documentation Sync**: Run `.kiro/hooks/sync-docs.sh` after changes

---

*Built using Spec-Driven Development with Kiro CLI - from user stories to production-ready architecture.*
