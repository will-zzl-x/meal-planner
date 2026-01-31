#!/bin/bash
# Documentation Sync Hook - Clean Architecture Focus
# Syncs steering files to docs/, excludes tests/ and specs/ for production focus

echo "🔄 Syncing steering files to documentation (Clean Architecture focus)..."

# Create docs structure
mkdir -p docs/product docs/technical docs/architecture

# Sync steering files to docs (production architecture only)
cp .kiro/steering/product.md docs/product/requirements.md
cp .kiro/steering/technical.md docs/technical/design.md  
cp .kiro/steering/architecture.md docs/architecture/overview.md
cp .kiro/steering/structure.md docs/technical/governance.md

# Copy implementation plan only (exclude other specs for focus)
cp specs/IMPLEMENTATION_PLAN.md docs/

echo "✅ Documentation sync complete!"
echo "📁 Production architecture documentation updated in docs/"
echo "🚫 Excluded tests/ and specs/ to maintain architecture focus"
echo "🎯 Future updates will target Windows environment"
